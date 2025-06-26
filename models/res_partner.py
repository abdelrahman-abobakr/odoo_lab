from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    related_patient_id = fields.Many2one(
        'hms.patient',
        string='Related Patient',
        help='Link this customer to a patient record',
        ondelete='set null',
        index=True
    )

    vat = fields.Char(
        string='Tax ID',
        help='Tax identification number',
        index=True,
        tracking=True
    )

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        processed_vals_list = []
        for vals in vals_list:
            processed_vals = self._prepare_create_vals(vals)
            processed_vals_list.append(processed_vals)

        records = super(ResPartner, self).create(processed_vals_list)

        for record in records:
            record._post_create_hms_integration()

        return records

    def _prepare_create_vals(self, vals):
        if vals.get('email') and not vals.get('related_patient_id'):
            patient = self._find_matching_patient(vals['email'])
            if patient:
                vals['related_patient_id'] = patient.id
        return vals

    def _find_matching_patient(self, email):
        if not email:
            return False
        Patient = self.env['hms.patient']
        return Patient.search([('email', '=', email)], limit=1)

    def _post_create_hms_integration(self):
        if self.related_patient_id:
            self._sync_customer_patient_data()

    def _sync_customer_patient_data(self):
        if not self.related_patient_id:
            return

        patient = self.related_patient_id
        sync_fields = ['phone', 'mobile', 'street', 'city', 'zip', 'country_id']

        for field in sync_fields:
            customer_value = getattr(self, field, False)
            patient_value = getattr(patient, field, False)

            if customer_value and not patient_value:
                setattr(patient, field, customer_value)

    def write(self, vals):
        result = super(ResPartner, self).write(vals)

        if 'related_patient_id' in vals:
            for record in self:
                if record.related_patient_id:
                    record._sync_customer_patient_data()

        contact_fields = ['phone', 'mobile', 'email', 'street', 'city', 'zip']
        if any(field in vals for field in contact_fields):
            for record in self:
                if record.related_patient_id:
                    record._sync_customer_patient_data()

        return result

    @api.constrains('vat')
    def _check_customer_vat(self):
        for record in self:
            if record.related_patient_id and not record.vat:
                raise ValidationError(
                    f"Customer '{record.name}' must have a Tax ID (VAT) number."
                )

    @api.constrains('related_patient_id', 'email')
    def _check_patient_email_match(self):
        for record in self:
            if record.related_patient_id and record.email and record.related_patient_id.email:
                if record.email.lower() != record.related_patient_id.email.lower():
                    raise ValidationError(
                        f"Customer email '{record.email}' does not match "
                        f"linked patient email '{record.related_patient_id.email}'. "
                        f"Please ensure emails match for proper integration."
                    )

    def action_link_to_patient(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Link to Patient',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('hms.view_customer_patient_link_wizard').id,
            'target': 'new',
        }

    def action_view_linked_patient(self):
        self.ensure_one()

        if not self.related_patient_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No patient is linked to this customer.',
                    'type': 'warning',
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Linked Patient',
            'res_model': 'hms.patient',
            'res_id': self.related_patient_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def search_customers_without_patients(self):
        return self.search([
            ('related_patient_id', '=', False),
            ('email', '!=', False)
        ])

    @api.model
    def search_patients_without_customers(self):
        linked_patient_ids = self.search([
            ('related_patient_id', '!=', False)
        ]).mapped('related_patient_id.id')

        Patient = self.env['hms.patient']
        return Patient.search([('id', 'not in', linked_patient_ids)])

    def unlink(self):
        patient_ids = self.mapped('related_patient_id.id')
        result = super(ResPartner, self).unlink()
        return result
