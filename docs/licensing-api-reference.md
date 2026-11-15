Integrate the Licensing API into this Registration app for four application categories: Company, Factory, Pharmacy, and Wholesale. Use the app’s existing backend, authentication, and UI conventions.

ACCESS

Set LICENSING_BASE_URL to the Licensing backend origin, for example https://licensing.example.com. Set LICENSING_REGISTRATION_API_KEY in the Registration app’s server environment. Its value must match REGISTRATION_API_KEY on the Licensing backend.

Send these headers on every request:

    X-API-KEY: <LICENSING_REGISTRATION_API_KEY>
    Accept: application/json

Call Licensing from the Registration app’s backend. Keep the API key in server-side configuration and enforce the Registration app’s own user permissions before returning records. Full details can contain national ID numbers, passport information, personal contact details, and document URLs. Return only the fields the current screen and user need.

ENDPOINTS

All eight endpoints use GET and require a trailing slash.

Company
    /api/applications/company/registration/list/
    /api/applications/company/registration/{application_id}/

Factory
    /api/applications/factory/registration/list/
    /api/applications/factory/registration/{application_id}/

Pharmacy
    /api/applications/pharmacy/registration/list/
    /api/applications/pharmacy/registration/{application_id}/

Wholesale
    /api/applications/wholesale/registration/list/
    /api/applications/wholesale/registration/{application_id}/

Use the singular category in the URL. When the user opens a list item, pass its category and exact application_id to the corresponding detail endpoint. URL-encode the application_id. Use category plus application_id as the record identity because the lookup is scoped to the category.

LIST RESPONSE

All four categories return the same list item shape:

{
  "application_id": "EXAMPLE-000001",
  "name": "Local business name",
  "name_en": "English business name",
  "aisa_license_number": null,
  "applicant": {
    "first_name_en": "Ahmad",
    "first_name_fa": "احمد",
    "last_name_en": "Ahmadi",
    "last_name_fa": "احمدی",
    "phone_number": "0700000000",
    "email": "owner@example.com"
  },
  "co_owner": null,
  "address": {
    "province": {
      "name_en": "Kabul",
      "name_fa": "کابل",
      "name_ps": "کابل"
    },
    "latitude": null,
    "longitude": null,
    "map_attachment": { "file": "https://licensing.example.com/media/map.pdf" }
  }
}

Company can return a value for aisa_license_number. Factory, Pharmacy, and Wholesale always return null for that list field. Pharmacy also always returns null for co_owner. For the other three categories, co_owner is null or has the same fields as applicant. Handle null applicant, province, coordinates, map_attachment, and map_attachment.file.

By default the API returns { "count": ..., "next": ..., "previous": ..., "results": [...] }. Use page and page_size to navigate. The default page size is 20 and the maximum is 100. With paginate=false, the API returns a plain array. Keep pagination enabled for interactive screens.

Lists include ongoing and completed applications and default to newest created first. Supported query parameters:

- Exact filters: name, application_id, address_provincename_en, addressdistrict_name_en, application_step, application_type, application_status.
- Search: search matches name and application_id.
- Ordering: application_step, name, created_at, updated_at. Prefix a field with "-" for descending order.

Example:
GET /api/applications/pharmacy/registration/list/?application_status=completed&address_province_name_en=Kabul&page=1&page_size=20

Some fields can be used as filters even though the list item does not return them. Read application_status, application_step, application_type, and district from the detail response when the UI needs their values.

DETAIL RESPONSE

The detail endpoint returns one full application object with no results wrapper. A direct lookup can return an application whose status excludes it from the list. Use the detail endpoint when a user opens a record.

Fields shared by all four detail responses:
- Identity and status: id, application_id, name, name_en, application_status, application_step, application_type, register_type, preferred_language, service_status, edit_lock.
- People and location: applicant, address, technical_staff, sharia_lawyer, sharia_lawyer_document, sharia_lawyer_jurisdiction, is_land_owned_by_applicant, land_ownership_attachment.
- Workflow: confirmations, caroky_delegation, opening_delegation, folder_details, rejected_by, rejection_reason, technical_applications, remove_technical_applications, change_location_applications, change_name_applications, change_owner_applications, change_sharia_lawyer_applications.
- Documents and finance: request_letter_attachment, stamp_attachment, extra_attachments, extra_notes, azade_press_request_letter_number, azade_press_response_attachment, finance_request_letter_number, finance_response_amount, finance_response_attachment.
- Audit: created_at, created_by, updated_at, updated_by.

Additional detail fields by category:

Company
- co_owner, activity_domain, is_llc, company_branches, warehouses, is_warehouse_nearby_company, change_co_owner_applications.
- aisa_license_number, aisa_license_attachment, aisa_license_issue_date, aisa_license_expire_date, issue_date, expiry_date, old_license_number, old_license_issue_date, old_license_attachment.
- bond_attachment, form_fee_receipt_amount, form_fee_receipt_attachment, sabt_markazy_letter_number, sabt_markazy_response_attachment, taxpayers_directorate_letter_number, taxpayers_directorate_response_attachment.

Factory
- co_owner, activity_domain, factory_branches, production_lines, build_delegation, change_co_owner_applications, is_technical_committee_approved, technical_committee_opinion.
- aisa_license_attachment, issue_date, expiry_date, old_license_number, old_license_issue_date, old_license_attachment, environmental_permit_license_number, environmental_permit_license_date, environmental_permit_license_attachment.
- factory_map_attachment, proposal_attachment, establishment_attachment, bond_attachment, form_fee_receipt_amount, form_fee_receipt_attachment, sabt_markazy_letter_number, sabt_markazy_response_attachment, taxpayers_directorate_letter_number, taxpayers_directorate_response_attachment.

Pharmacy
- pharmacy_type, grade, is_owner_and_technical_same.
- license_attachment, license_issue_date, license_expiry_date, ibn_sina_procurement_attachment.
- archive, archive_id, survey, survey_id.

Wholesale
- co_owner, activity_domain, warehouses, is_warehouse_nearby_wholesale.
- license_attachment, issue_date, old_license_number, old_license_issue_date, old_license_attachment.
- bond_attachment, form_fee_receipt_amount, form_fee_receipt_attachment, ibn_sina_procurement_attachment, sabt_markazy_letter_number, sabt_markazy_response_attachment, taxpayers_directorate_letter_number, taxpayers_directorate_response_attachment.
- archive, archive_id, survey, survey_id.

The detail address includes id, province, district, address, map_attachment, latitude, longitude, and total_area. Company and Factory additionally expose long_lat. Detail applicant and co_owner objects are richer than their list equivalents and can include identity, address, and document fields. Model the detail response by category and render optional values defensively.

IMPLEMENTATION

Create a shared server-side Licensing client with two operations: listApplications(category, filters) and getApplication(category, applicationId). Allow only the four categories above. Use the list operation for search and selection, and fetch details on demand.

Handle empty results, 400 for invalid filters, 401 or 403 for authentication failures, 404 for a missing detail record, and upstream timeouts. Keep API keys and personal data out of logs. Verify all four categories, both list response formats, null optional fields, and detail lookup by application_id