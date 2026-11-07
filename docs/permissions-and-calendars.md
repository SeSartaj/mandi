# Permissions and calendars

## Permission groups

`accounts.0002_predefined_groups` installs six groups with explicit Django permissions. Fresh databases receive them during `migrate`; `seed_demo` only assigns existing groups. The migration upgrades the original Review managers and Review readers group names.

| Group | Access |
| --- | --- |
| Mandi administrators | Read domain records; manage establishments/source connections; ingest and approve inspections; manage checklists, XLSForms, and KoBo deployment; create employees and assign predefined groups |
| Mandi registry officers | Read domain records; create/edit establishments and connect external records |
| Mandi inspectors | Read establishments, source links, inspections, checklists, and employee directory |
| Mandi inspection reviewers | Read domain records; approve inspections |
| Mandi viewers | Read domain records and employee directory |
| Mandi integration operators | Read domain records; ingest inspection summaries; deploy checklists to KoBo |

No role automatically gains newly introduced permissions. These are Django groups, not staff/superuser flags. Django administration access remains a separate account setting.

The copied CMS `Can`/`CanAny` components now guard navigation, routes, and protected actions. They support a single permission, OR/AND combinations, fallback content, and optional staff checks. They use Mandi's authenticated session rather than the CMS account store. API services remain authoritative: hiding a button is not the security boundary.

Employee creation offers the predefined groups through the copied multi-select search component. Assigning groups requires `accounts.change_user` in addition to `accounts.add_user`; listing groups requires `auth.view_group`. The service accepts only known predefined Mandi group IDs. Existing employees can also be assigned groups through Django account administration.

## Form components

The CMS custom form components and dependencies are copied under `mandi_frontend/src/components/ui/custom`, including CustomForm, CustomInput, CustomSelect, CustomTextarea, both date pickers, CustomSearchSelector, CustomFileInput, checkbox, radio, switch, SearchableSelect, and InputLayout. The shared FormField and form utilities are copied too.

Login, establishment creation/editing, inspection filters, and employee creation/group selection use the copied components. React Hook Form owns their values and validation. The file component is available for checklist-specific fields; no artificial fields were added solely to use it.

## Calendar contract

The copied CMS header includes the calendar selector. Gregorian, Shamsi, and Qamari choices persist under `calendar-format`; the shared calendar hook also understands the CMS legacy `gregorian` and `hijri` values.

- Date pickers render the selected calendar and convert values to ASCII Gregorian `YYYY-MM-DD` before submission.
- Changing the header selection updates mounted pickers and displayed dates without changing their stored values.
- Inspection dates, deadlines, and approval timestamps display in the selected calendar. Timestamp display uses Asia/Kabul.
- Backend structured date fields and date filters remain Gregorian. The unused alternate-calendar inspection columns have been removed by `inspections.0003`.
- Qamari uses the CMS date picker's calculated Islamic calendar. The CMS's separate observed-month/sighting service and corrections have not been ported; no source API or credentials are reused.

Browser verification selected Qamari 1448-05-23 and observed the API request `date_from=2026-11-04`. Shamsi and Gregorian display were also checked.

## Verification

27 backend tests pass, including fresh migration group provisioning, explicit role grants, API denial, group assignment/escalation protection, the CMS page-size contract, the checklist XLSForm API, KoBo deployment permissions and failure recording, and existing inspection workflows. Three frontend tests cover Can behavior, Shamsi leap-year boundaries, and Qamari/Shamsi round trips to Gregorian. Browser checks verify a viewer has no add action and receives permission denial on a protected direct route, and that administrators see all six groups in employee creation.
