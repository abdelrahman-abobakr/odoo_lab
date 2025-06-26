from odoo import models, fields, api

class HmsDoctor(models.Model):
    _name = 'hms.doctor'
    _description = 'HMS Doctor'
        
    first_name = fields.Char(string='First Name', required=True)
    last_name = fields.Char(string='Last Name', required=True)
    name = fields.Char(string='Full Name', compute='_compute_name', store=True)
    image = fields.Binary(string='Image')
        
    patient_ids = fields.Many2many('hms.patient', string='Patients')
        
    patient_count = fields.Integer(
        string='Patient Count',
        compute='_compute_patient_count',
        store=True  
    )

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for record in self:
            if record.first_name and record.last_name:
                record.name = f"{record.first_name} {record.last_name}"
            elif record.first_name:
                record.name = record.first_name
            elif record.last_name:
                record.name = record.last_name
            else:
                record.name = ""
        
    def _compute_patient_count(self):
        for doctor in self:
            doctor.patient_count = len(doctor.patient_ids)
        
    def name_get(self):
        result = []
        for doctor in self:
            name = f"Dr. {doctor.first_name} {doctor.last_name}"
            result.append((doctor.id, name))
        return result