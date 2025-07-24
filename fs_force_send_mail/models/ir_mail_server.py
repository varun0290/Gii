# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


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