# Turn on signed tables
db._common_fields.append(auth.signature)

# --------------------------------------------------------------------------------
# GLOBAL LIST DEFINITIONS
# --------------------------------------------------------------------------------

# An assignment is first created, then set to the marker (becoming Not started).
# Once someone has saved a partial record it becomes Started and then once
# Submitted it becomes readonly to all but admins. Once Released, students are
# able to download it. Arguably this is CSS. Okay, not arguably. It _is_ CSS.

status_dict = {
    "Created": SPAN(
        "",
        _class="fa fa-check",
        _style="color:grey;font-size: 1.3em;",
        _title="Created",
    ),
    "Not started": SPAN(
        "",
        _class="fa fa-pencil-square-o",
        _style="color:#ca0020;font-size: 1.3em;",
        _title="Not started",
    ),
    "Started": SPAN(
        "",
        _class="fa fa-pencil-square-o",
        _style="color:#f4a582;font-size: 1.3em;",
        _title="Started",
    ),
    "Submitted": SPAN(
        "",
        _class="fa fa-pencil-square-o",
        _style="color:#0571b0;font-size: 1.3em;",
        _title="Submitted",
    ),
    "Released": SPAN(
        "",
        _class="fa fa-eye",
        _style="color:green;font-size: 1.3em;",
        _title="Released",
    ),
}

## --------------------------------------------------------------------------------
## TABLE DEFINITIONS
## --------------------------------------------------------------------------------

#
# Refactor to integrated marking/projects notes and magic_links
# - db.markers -> db.project_staff?
# - Add fields to db.project_staff:
#    - Location/Institution.
#    - Research Interests.
#    - Internal (can supervise as sole)

# - Update authenticate to use magic_link and finesse session expiry and inactivity
#   settings.
# - Update projects to link to project_staff.
#    - add lead supervisor field and
#    - add lead_is_internal field?
#    - add interal supervisor field then internal
#    - add status: Saved/Available/Filled/Hidden
#   - Cannot publish a project without an internal.
#
#   Provide a review projects link (or allow project_staff a less filtered view of
#   project_proposals), so that they can see _all_ projects including unpublished ones,
#   so internals can review external projects?

# Links through to replace project database:
#  - Add filled_by field to link to student?
#    This makes a project a specific project in a specific year.
#  - Add a clone option to my_projects.
#  - Project then needs ability to update - who can change? Simplest to
#    have this being supervisor, otherwise need student validation
#    and review. Does it actually need _versioning_? Only really to
#    preserve historical record but could have save with filled mark
#    as hidden and create copy?
#  - Also needs option to _withdraw_ student. Again - save record but
#    archive? This may need _admin_ approval.

db.define_table(
    "markers",
    Field("first_name", "string"),
    Field("last_name", "string"),
    Field("email", "string", requires=IS_EMAIL()),
    Field("is_internal", "boolean", default=False),
    Field(
        "marker_access_token",
        length=64,
        default=uuid.uuid4,
        readable=False,
        writable=False,
    ),
    format="%(first_name)s %(last_name)s",
)

# This table maintains a list of available marking roles and the form
# and marking criteria associated with each

db.define_table(
    "marking_roles",
    Field("name", "string", notnull=True),
    Field("role_class", "string", notnull=True),
    Field("marking_criteria", "string", notnull=True),
    Field("form_file", "string", notnull=True),
    Field("form_json", "json", notnull=True),
    Field("is_active", "boolean", default=False),
    format="%(name)s",
)

# This table records what the assignments are. The data field holds a JSON object
# containing the content of the variables listed in the correct report
# template which is defined by the marking form.

db.define_table(
    "assignments",
    Field("student_presentation", "reference student_presentations"),
    Field("marker", "reference teaching_staff"),
    Field("marker_role_id", "reference marking_roles"),
    Field("assignment_data", "json"),
    Field("due_date", "date", notnull=True, requires=IS_DATE()),
    Field("submission_date", "datetime", readable=False, writable=False),
    Field("submission_ip", "string", readable=False, writable=False),
    Field(
        "status",
        requires=IS_IN_SET(list(status_dict.keys())),
        default="Created",
        writable=False,
    ),
    # migrate=False, fake_migrate=True,
)


# This table stores data about the files held in sharepoint that are to be provided
# to markers. Typically, this is thesis files to Markers, but could be any combination
# of presentation and role. The unique id provides a permanent reference to retrieve
# file details from the Sharepoint API

# The order here is a little bit arbitrary, but since the year and role are
# unlikely to change, they come further down the structure

# 'EEC_MSc/2020/Marker/Orme_EEC_MSc_00206010.pdf'

db.define_table(
    "marking_files",
    Field("unique_id", length=64),
    Field("filename", "string"),
    Field("relative_url", "string"),
    Field("marker_role_id", "reference marking_roles"),
    Field("student", "reference student_presentations"),
    Field("matching_issues", "string"),
)
