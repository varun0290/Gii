# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def build_email(
        self,
        email_from,
        email_to,
        subject,
        body,
        email_cc=None,
        email_bcc=None,
        reply_to=False,
        attachments=None,
        message_id=None,
        references=None,
        object_id=False,
        subtype="plain",
        headers=None,
        body_alternative=None,
        subtype_alternative="plain",
    ):
        # smtp = self.env["ir.mail_server"].search(
        #     [("company_id", "=", self.env.company.id)], limit=1
        # )
        smtp = self.env["ir.mail_server"].search([], limit=1)
        uid = self._context.get("uid")
        user_id = self.env["res.users"].browse(uid)
        email_from = "%s <%s>" % (user_id.name, smtp.smtp_user) or email_from
        reply_to = "%s <%s>" % (user_id.name, smtp.smtp_user) or email_from
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
