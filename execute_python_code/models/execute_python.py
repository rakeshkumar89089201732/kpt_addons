from odoo import models, fields, api, _
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
import datetime
import base64

class ExecutePython(models.Model):
    
    _name = "execute.python.code"
    _description = "Execute Python Code"
    
    name = fields.Char(string='Name',required=True)
    code = fields.Text(string='Python Code',default="# Place your code below.\n\n\n\n\n\n\n\n")
    result = fields.Text(string='Result',readonly=True)
    active = fields.Boolean(string="Active",default=True)
    datas = fields.Binary(string="Binay Code",compute="_convert_to_binay")
    last_execution_date = fields.Datetime(string="Last execution on")
    track_error_with_log = fields.Boolean(string="Track error with log ?",default=False)
    
    def toggle_active(self):
        for record in self:
            record.write({'active': not record.active})
        
    def _convert_to_binay(self):
        for record in self:
            record.datas = base64.b64encode(record.code.encode())
        
    def download_code(self):
        return {
                'type' : 'ir.actions.act_url',
                'url':'web/content/?model=execute.python.code&download=true&field=datas&id=%s&filename=%s.py'%(self.id,self.name),
                'target': 'new',
            }
    
    def unlink(self):
        self.write({'active':False})
        return True
        
    def execute_code(self):
        localdict = {'self':self,'user_obj':self.env.user}
        for obj in self: #.browse(self._ids):
            if not obj.code:
                continue
            
            if obj.track_error_with_log:
                exec(obj.code,localdict)
                if localdict.get('result', False):
                    self.write({'result':localdict['result']})
                else : 
                    self.write({'result':False})
                self.write({'last_execution_date':datetime.datetime.now()})
            else:
                try :
                    exec(obj.code,localdict)
                    if localdict.get('result', False):
                        self.write({'result':localdict['result']})
                    else : 
                        self.write({'result':False})
                    self.write({'last_execution_date':datetime.datetime.now()})
                except Exception as e:
                    raise ValidationError('Python code is not able to run ! message : %s' %(e))
        return True