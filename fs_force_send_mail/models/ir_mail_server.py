# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from collections import defaultdict


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _split_by_mail_configuration(self):
        """Group the <mail.mail> based on their "email_from", their "alias domain"
        and their "mail_server_id".

        The <mail.mail> will have the "same sending configuration" if they have the same
        mail server, alias domain and mail from. For performance purpose, we can use an SMTP
        session in batch and therefore we need to group them by the parameter that will
        influence the mail server used.

        The same "sending configuration" may repeat in order to limit batch size
        according to the `mail.session.batch.size` system parameter.

        Return iterators over
            mail_server_id, email_from, Records<mail.mail>.ids
        """
        mail_values = self.read(['id', 'email_from', 'mail_server_id', 'record_alias_domain_id'])

        # First group the <mail.mail> per mail_server_id, per alias_domain (if no server) and per email_from
        group_per_email_from = defaultdict(list)
        for values in mail_values:
            mail_server_id = values['mail_server_id'][0] if values['mail_server_id'] else False
            alias_domain_id = values['record_alias_domain_id'][0] if values['record_alias_domain_id'] else False
            key = (mail_server_id, alias_domain_id, values['email_from'])
            group_per_email_from[key].append(values['id'])

        # Then find the mail server for each email_from and group the <mail.mail>
        # per mail_server_id and smtp_from
        mail_servers = self.env['ir.mail_server'].sudo().search([], order='sequence, id')
        group_per_smtp_from = defaultdict(list)
        for (mail_server_id, alias_domain_id, email_from), mail_ids in group_per_email_from.items():
            if not mail_server_id:
                mail_server = self.env['ir.mail_server']
                if alias_domain_id:
                    alias_domain = self.env['mail.alias.domain'].sudo().browse(alias_domain_id)
                    mail_server = mail_server.with_context(
                        domain_notifications_email=alias_domain.default_from_email,
                        domain_bounce_address=alias_domain.bounce_email,
                    )
                mail_server = self.env['ir.mail_server'].search([], limit=1)
                if mail_server:
                    mail_server, smtp_from = mail_server, mail_server.smtp_user
                    mail_server_id = mail_server.id if mail_server else False
                else:
                    mail_server, smtp_from = mail_server._find_mail_server(email_from, mail_servers)
                    mail_server_id = mail_server.id if mail_server else False
            else:
                mail_server = self.env['ir.mail_server'].search([], limit=1)
                smtp_from = mail_server.smtp_user or email_from

            group_per_smtp_from[(mail_server_id, alias_domain_id, smtp_from)].extend(mail_ids)

        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.session.batch.size')) or 1000
        for (mail_server_id, alias_domain_id, smtp_from), record_ids in group_per_smtp_from.items():
            for batch_ids in tools.split_every(batch_size, record_ids):
                yield mail_server_id, alias_domain_id, smtp_from, batch_ids
        

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _send_email(
        self,
        message,
        mail_server_id=None,
        smtp_server=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_encryption=None,
        smtp_debug=False,
        smtp_session=None
    ):
        """ Override to ensure the From header uses SMTP user when no from_filter is set """
        # Get the mail server
        mail_server = None
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
        elif not smtp_server:
            mail_server = self.sudo()._find_mail_server(self.env.user.company_id.id)

        # If we have a mail server, ensure the From header is properly set
        if mail_server:
            if not mail_server.from_filter and mail_server.smtp_user:
                message.replace_header('From', mail_server.smtp_user)
            elif mail_server.smtp_from:
                message.replace_header('From', mail_server.smtp_from)

        # Call original method
        return super(IrMailServer, self)._send_email(
            message, mail_server_id=mail_server_id, smtp_server=smtp_server,
            smtp_port=smtp_port, smtp_user=smtp_user, smtp_password=smtp_password,
            smtp_encryption=smtp_encryption, smtp_debug=smtp_debug,
            smtp_session=smtp_session
        )

    def build_email(
        self,
        email_from,
        email_to,
        subject,
        body,
        email_cc=None,
        email_bcc=None,
        reply_to=None,
        attachments=None,
        message_id=None,
        references=None,
        object_id=False,
        subtype="plain",
        headers=None,
        body_alternative=None,
        subtype_alternative="plain",
    ):
        # Get the first available mail server
        mail_server = self.env['ir.mail_server'].search([], limit=1)

        # Get the current user
        user = self.env.user

        # Only override if we found a mail server and it has smtp_user set
        if mail_server and mail_server.smtp_user:
            email_from = f"{user.name} <{mail_server.smtp_user}>"
            if reply_to is None:
                reply_to = email_from

        return super(IrMailServer, self).build_email(
            email_from=email_from,
            email_to=email_to,
            subject=subject,
            body=body,
            email_cc=email_cc,
            email_bcc=email_bcc,
            reply_to=reply_to,
            attachments=attachments,
            message_id=message_id,
            references=references,
            object_id=object_id,
            subtype=subtype,
            headers=headers,
            body_alternative=body_alternative,
            subtype_alternative=subtype_alternative,
        )