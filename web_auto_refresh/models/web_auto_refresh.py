# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


# import openerp
# from openerp.models import BaseModel
from openerp import models, api
from openerp.models import BaseModel
from openerp.http import WebRequest, _request_stack, request

import logging

_logger = logging.getLogger(__name__)


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    @api.model
    def create(self, vals):
        res = super(MailNotification, self).create(vals)
        bus = self.env['bus.bus']
        user_obj = self.env['res.users']
        users = user_obj.search([('partner_id', '=', res.partner_id.id)])
        for user in users:
            bus.sendone(self._name, user.id)
        return res


def __exit__(self, exc_type, exc_value, traceback):
    _request_stack.pop()

    if self._cr:
        if exc_type is None and not self._failed:
            if self.params and 'model' in self.params:
                model = self.env[self.params['model']]
                ids = False
                if 'args' in self.params and self.params['args']:
                    ids = self.params['args'][0]
                elif 'id' in self.params and self.params['id']:
                    ids = [self.params['id']]
                if 'update_db' in self.params and self.params['update_db']:
                    auto_refresh_kanban_list(model, 'write', ids)
                elif 'insert_db' in self.params and self.params['insert_db']:
                    auto_refresh_kanban_list(model, 'create', ids)
                elif 'delete_db' in self.params and self.params['delete_db']:
                    auto_refresh_kanban_list(model, 'unlink', ids)
            # Connector Support
            elif self.params and 'job_uuid' in self.params and \
                    'queue.job' in self.registry.models:
                job_uuid = self.params['job_uuid']
                job = self.env['queue.job'].sudo().\
                    search([('uuid', '=', job_uuid)])
                model = self.env[job.model_name]
                try:
                    form_id = int(job.func_string.split(
                        job.model_name + "',")[1].split(')')[0])
                except (IndexError, ValueError):
                    pass
                else:
                    auto_refresh_kanban_list(model, 'connector', [form_id])
            self._cr.commit()
        self._cr.close()
    # just to be sure no one tries to re-use the request
    self.disable_db = True
    self.uid = None


WebRequest.__exit__ = __exit__


write_original = BaseModel.write


@api.multi
def write(self, vals):
    result = write_original(self, vals)
    try:
        request.params['update_db'] = True
    except RuntimeError:
        pass
    return result


BaseModel.write = write


create_original = BaseModel.create


@api.model
@api.returns('self', lambda value: value.id)
def create(self, vals):
    record_id = create_original(self, vals)
    try:
        request.params['insert_db'] = True
    except RuntimeError:
        pass
    return record_id


BaseModel.create = create


unlink_original = BaseModel.unlink


@api.multi
def unlink(self):
    result = unlink_original(self)
    try:
        request.params['delete_db'] = True
    except RuntimeError:
        pass
    return result


BaseModel.unlink = unlink


def auto_refresh_kanban_list(model, method, ids):
    if model._name != 'bus.bus':
        module = model._name.split('.')[0]
        if module not in ['ir', 'res', 'base', 'bus', 'im_chat', 'mail',
                          'email', 'temp', 'workflow', 'wizard',
                          'email_template', 'mass']:
            action = model.env['ir.actions.act_window']
            cnt = action.search_count([('res_model', '=', model._name),
                                       ('auto_refresh', '>', '0')])
            if cnt > 0:
                with api.Environment.manage():
                    new_cr = model.pool.cursor()
                    new_env = api.Environment(new_cr, model._uid,
                                              model._context)
                    self = new_env[model._name]
                    bus = self.env['bus.bus']
                    if ids and isinstance(ids, (list, tuple)):
                        bus.sendone('auto_refresh_kanban_list',
                                    [model._name, method,
                                     model.env.user.id, ids])
                    else:
                        bus.sendone('auto_refresh_kanban_list',
                                    [model._name, method, model.env.user.id])
                    self._cr.commit()
                    self._cr.close()
