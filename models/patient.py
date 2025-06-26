from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class HmsPatient(models.Model):
    _name = 'hms.patient'
    _description = 'HMS Patient'
        
    first_name = fields.Char(string='First Name', required=True)
    last_name = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email', required=True)
    birth_date = fields.Date(string='Birth Date')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    cr_ratio = fields.Float(string='CR Ratio')
    blood_type = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], string='Blood Type')
    pcr = fields.Boolean(string='PCR')
    image = fields.Binary(string='Image')
    address = fields.Text(string='Address')
    history = fields.Text(string='History')
        
    state = fields.Selection([
        ('undetermined', 'Undetermined'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('serious', 'Serious'),
    ], default='undetermined', string='State')

    department_id = fields.Many2one('hms.department', string='Department')
    doctor_ids = fields.Many2many('hms.doctor', string='Doctors')

    department_capacity = fields.Integer(
        string='Department Capacity',
        related='department_id.capacity',
        readonly=True
    )
    
    log_ids = fields.One2many('hms.patient.log', 'patient_id', string='Logs')
    
    @api.depends('birth_date')
    def _compute_age(self):
        for record in self:
            if record.birth_date:
                from datetime import date
                today = date.today()
                record.age = today.year - record.birth_date.year - (
                    (today.month, today.day) < (record.birth_date.month, record.birth_date.day)
                )
            else:
                record.age = 0

    @api.onchange('age')
    def _onchange_age(self):
        """Auto-check PCR if age is less than 30 and show warning"""
        if self.age and self.age < 30 and not self.pcr:
            self.pcr = True
            return {
                'warning': {
                    'title': 'PCR Auto-checked',
                    'message': 'PCR has been automatically checked because the patient is under 30 years old.'
                }
            }

    @api.onchange('birth_date')
    def _onchange_birth_date(self):
        """Trigger age computation and PCR check when birth date changes"""
        if self.birth_date:
            from datetime import date
            today = date.today()
            calculated_age = today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
            if calculated_age < 30 and not self.pcr:
                self.pcr = True
                return {
                    'warning': {
                        'title': 'PCR Auto-checked',
                        'message': 'PCR has been automatically checked because the patient is under 30 years old.'
                    }
                }

    @api.constrains('email')
    def _check_email_format(self):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for record in self:
            if record.email and not re.match(email_pattern, record.email):
                raise ValidationError(f"Invalid email format: {record.email}")

    @api.constrains('email')
    def _check_email_unique(self):
        """Ensure email is unique across all patients"""
        for record in self:
            if record.email:
                existing_patient = self.search([
                    ('email', '=', record.email),
                    ('id', '!=', record.id)
                ])
                if existing_patient:
                    raise ValidationError(f"Email '{record.email}' already exists for another patient.")

    @api.constrains('pcr', 'cr_ratio')
    def _check_cr_ratio_when_pcr(self):
        """Validate CR ratio is provided when PCR is checked"""
        for record in self:
            if record.pcr and not record.cr_ratio:
                raise ValidationError("CR Ratio is mandatory when PCR is checked.")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if vals.get('state'):
            record._create_state_log(vals['state'])
        return record

    def write(self, vals):
        if 'state' in vals:
            for patient in self:
                if patient.state != vals['state']:
                    patient._create_state_log(vals['state'])
        return super().write(vals)

    def _create_state_log(self, new_state):
        self.env['hms.patient.log'].create({
            'patient_id': self.id,
            'description': f"State changed to {new_state.capitalize()}",
        })

    def name_get(self):
        """Override name_get to display full patient name"""
        result = []
        for record in self:
            name = f"{record.first_name} {record.last_name}" if record.first_name and record.last_name else ""
            result.append((record.id, name))
        return result