# -*- coding: utf-8 -*-

import base64
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class HrDocumentPortal(CustomerPortal):

    def _document_get_page_view_values(self, line, access_token, **kwargs):
        return {
            'line': line,
            'token': access_token,
            'page_name': 'hr_document',
            'document_url': '/my/document/%s?access_token=%s' % (line.id, access_token),
            'download_url': '/my/document/%s/download?access_token=%s' % (line.id, access_token),
            'ack_url': '/my/document/%s/acknowledge?access_token=%s' % (line.id, access_token),
        }

    @http.route(
        ['/my/documents', '/my/documents/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_my_documents(self, page=1, **kw):
        """List documents (deployment lines) for current user's employee."""
        Partner = request.env['res.partner'].sudo()
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid),
            ('work_contact_id', '=', partner.id),
        ], limit=1)
        if not employee:
            employee = request.env['hr.employee'].sudo().search([
                ('user_id.partner_id', '=', partner.id),
            ], limit=1)
        if not employee:
            return request.render(
                'fs_hr_document_management.portal_my_documents_empty',
                {'page_name': 'hr_document'},
            )
        lines = request.env['hr.document.deployment.line'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '!=', 'draft'),
        ], order='create_date desc')
        values = {
            'lines': lines,
            'employee': employee,
            'page_name': 'hr_document',
        }
        return request.render(
            'fs_hr_document_management.portal_my_documents',
            values,
        )

    @http.route(
        ['/my/document/<int:line_id>'],
        type='http',
        auth='public',
        website=True,
    )
    def portal_document_view(self, line_id, access_token=None, **kw):
        """View document - requires token for public access."""
        line = request.env['hr.document.deployment.line'].sudo().browse(line_id)
        if not line.exists():
            return request.redirect('/my')
        if not access_token or line.access_token != access_token:
            return request.redirect('/my')
        line.action_mark_viewed()
        values = self._document_get_page_view_values(line, access_token, **kw)
        return request.render(
            'fs_hr_document_management.portal_document_view',
            values,
        )

    @http.route(
        ['/my/document/<int:line_id>/download'],
        type='http',
        auth='public',
        website=True,
    )
    def portal_document_download(self, line_id, access_token=None, **kw):
        """Download document PDF."""
        line = request.env['hr.document.deployment.line'].sudo().browse(line_id)
        if not line.exists() or not access_token or line.access_token != access_token:
            return request.redirect('/my')
        attach = line.document_attachment_id
        if not attach or not attach.datas:
            return request.redirect('/my')
        return request.make_response(
            base64.b64decode(attach.datas),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="%s"' % (attach.name or 'document.pdf')),
            ],
        )

    @http.route(
        ['/my/document/<int:line_id>/acknowledge'],
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        website=True,
    )
    def portal_document_acknowledge(self, line_id, access_token=None, **kw):
        """E-sign / acknowledge the document."""
        line = request.env['hr.document.deployment.line'].sudo().browse(line_id)
        if not line.exists() or not access_token or line.access_token != access_token:
            return request.redirect('/my')
        if line.state == 'signed':
            return request.redirect('/my/document/%s?access_token=%s' % (line_id, access_token))
        if request.httprequest.method == 'POST':
            full_name = kw.get('full_name') or ''
            employee_code = kw.get('employee_code') or ''
            if full_name and employee_code:
                line.action_acknowledge(full_name, employee_code)
                return request.redirect('/my/documents')
        values = self._document_get_page_view_values(line, access_token, **kw)
        return request.render(
            'fs_hr_document_management.portal_document_acknowledge',
            values,
        )
