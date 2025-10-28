from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class MailMeassge(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, values_list):
        res = super(MailMeassge, self).create(values_list)
        mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
        if mail_server:
        	res.write({"email_from": mail_server.sudo().smtp_user})
        return res


# class MailMail(models.Model):
#     _inherit = 'mail.mail'
    
#     def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
#         # Separate mails with custom email_from
#         custom_from_mails = self.filtered(lambda m: m.email_from and m.mail_server_id)
#         normal_mails = self - custom_from_mails
#         # Process mails with custom email_from
#         for mail in custom_from_mails:
#             try:
#                 # Get the prepared email values
#                 body = mail._send_prepare_values()
#                 # Override the from address with our custom email
#                 effective_from = mail.mail_server_id.smtp_user or mail.email_from
#                 # Connect to SMTP server
#                 if smtp_session is None:
#                     smtp_session = self.env['ir.mail_server']._connect_smtp(
#                         mail.mail_server_id, mail.mail_server_id.id
#                     )
#                 # Send the email with custom from address
#                 self.env['ir.mail_server'].send_email(
#                     message=body['message'],
#                     mail_server_id=mail.mail_server_id.id,
#                     smtp_session=smtp_session,
#                     from_addr=effective_from,
#                     to_addrs=body['email_to'],
#                     cc_addrs=body.get('email_cc'),
#                     bcc_addrs=body.get('email_bcc'),
#                     reply_to=body.get('reply_to'),
#                     attachments=body.get('attachments'),
#                     message_id=body.get('message_id'),
#                     references=body.get('references'),
#                     subject=body.get('subject'),
#                 )
#                 mail.write({'state': 'sent'})
#                 _logger.info('Email sent with custom from: %s', effective_from)
                
#             except Exception as e:
#                 _logger.error('Failed to send email with custom from: %s', str(e))
#                 if raise_exception:
#                     raise
#                 mail.write({'state': 'exception', 'failure_reason': str(e)})
#         # Process normal mails with original method
#         if normal_mails:
#             return super(MailMail, normal_mails)._send(
#                 auto_commit=auto_commit,
#                 raise_exception=raise_exception,
#                 smtp_session=smtp_session
#             )
#         return True


# class IrMailServer(models.Model):
#     _inherit = "ir.mail_server"

#     def _send_email(
#         self,
#         message,
#         mail_server_id=None,
#         smtp_server=None,
#         smtp_port=None,
#         smtp_user=None,
#         smtp_password=None,
#         smtp_encryption=None,
#         smtp_debug=False,
#         smtp_session=None
#     ):
#         """ Override to ensure the From header uses SMTP user when no from_filter is set """
#         # Get the mail server
#         mail_server = None
#         if mail_server_id:
#             mail_server = self.sudo().browse(mail_server_id)
#         elif not smtp_server:
#             mail_server = self.sudo()._find_mail_server(self.env.user.company_id.id)

#         # If we have a mail server, ensure the From header is properly set
#         if mail_server:
#             if not mail_server.from_filter and mail_server.smtp_user:
#                 message.replace_header('From', mail_server.smtp_user)
#             elif mail_server.smtp_from:
#                 message.replace_header('From', mail_server.smtp_from)

#         # Call original method
#         return super(IrMailServer, self)._send_email(
#             message, mail_server_id=mail_server_id, smtp_server=smtp_server,
#             smtp_port=smtp_port, smtp_user=smtp_user, smtp_password=smtp_password,
#             smtp_encryption=smtp_encryption, smtp_debug=smtp_debug,
#             smtp_session=smtp_session
#         )

#     def build_email(
#         self,
#         email_from,
#         email_to,
#         subject,
#         body,
#         email_cc=None,
#         email_bcc=None,
#         reply_to=None,
#         attachments=None,
#         message_id=None,
#         references=None,
#         object_id=False,
#         subtype="plain",
#         headers=None,
#         body_alternative=None,
#         subtype_alternative="plain",
#     ):
#         # Get the first available mail server
#         mail_server = self.env['ir.mail_server'].search([], limit=1)

#         # Get the current user
#         user = self.env.user

#         # Only override if we found a mail server and it has smtp_user set
#         if mail_server and mail_server.smtp_user:
#             email_from = f"{user.name} <{mail_server.smtp_user}>"
#             if reply_to is None:
#                 reply_to = email_from

#         return super(IrMailServer, self).build_email(
#             email_from=email_from,
#             email_to=email_to,
#             subject=subject,
#             body=body,
#             email_cc=email_cc,
#             email_bcc=email_bcc,
#             reply_to=reply_to,
#             attachments=attachments,
#             message_id=message_id,
#             references=references,
#             object_id=object_id,
#             subtype=subtype,
#             headers=headers,
#             body_alternative=body_alternative,
#             subtype_alternative=subtype_alternative,
#         )