from odoo import models, fields, api

class PatientLog(models.Model):
    _name = 'hms.patient.log'
    _description = 'Patient Log'

    patient_id = fields.Many2one('hms.patient', string='Patient', ondelete='cascade')
    
    patient_name = fields.Char(string='Patient Name', compute='_compute_patient_name', store=True)
   
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    description = fields.Text(string='Description')

    @api.depends('patient_id', 'patient_id.first_name', 'patient_id.last_name')
    def _compute_patient_name(self):
        for record in self:
            if record.patient_id:
                record.patient_name = f"{record.patient_id.first_name} {record.patient_id.last_name}"
            else:
                record.patient_name = ""