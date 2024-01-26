from itertools import groupby
import csv
import io


@auth.requires(
    auth.has_membership(auth.id_group("admin"))
    or auth.has_membership(auth.id_group("timetabler"))
)
def teaching_staff():
    """Presents a view of teaching staff.

    Admins and timetablers can add and edit, and see inactive staff.
    """

    db.teaching_staff.id.readable = True
    db.teaching_staff._common_filter = None

    form = SQLFORM.grid(
        db.teaching_staff,
        details=False,
        create=True,
        editable=True,
        deletable=False,
        csv=True,
        ignore_common_filters=True,
    )

    return dict(form=form)


@auth.requires_membership("admin")
def students():
    # don't allow deleting as the referencing to project marks will
    # drop referenced rows from marking tables
    form = SQLFORM.grid(db.students, csv=False, deletable=False)

    return dict(form=form)


@auth.requires_membership("admin")
def courses():
    # don't allow deleting as the referencing will
    # drop referenced rows from marking tables

    db.courses.common_filters = None

    form = SQLFORM.grid(db.courses, csv=False, deletable=False)

    return dict(form=form)


@auth.requires_membership("admin")
def student_presentations():
    # don't allow deleting as the referencing will
    # drop referenced rows from marking tables
    form = SQLFORM.grid(db.student_presentations, csv=False, deletable=False)

    return dict(form=form)


@auth.requires_membership("admin")
def presentations():
    # don't allow deleting as the referencing to project marks will
    # drop referenced rows from marking tables
    form = SQLFORM.grid(db.course_presentations, csv=False, deletable=False)

    return dict(form=form)


@auth.requires_membership("admin")
def load_students():
    # Get lookups for courses and active presentations, using a left join to allow
    # for courses with no presentations.
    active_presentations = db().select(
        db.courses.id,
        db.courses.abbrname,
        db.course_presentations.id,
        db.course_presentations.name,
        db.course_presentations.is_active,
        orderby=[db.courses.id],
        left=db.course_presentations.on(
            db.courses.id == db.course_presentations.course
        ),
    )

    # id maps
    active_pres_map = {
        ky: [v.course_presentations.id for v in vl if v.course_presentations.is_active]
        for ky, vl in groupby(active_presentations, key=lambda val: val.courses.id)
    }
    course_map = {v.courses.abbrname: v.courses.id for v in active_presentations}

    known_courses = list(course_map.keys())

    # Expose the upload form
    form = FORM(
        DIV(
            DIV("Upload File:", _class="col-sm-2"),
            DIV(
                INPUT(
                    _type="file", _name="myfile", id="myfile", requires=IS_NOT_EMPTY()
                ),
                _class="col-sm-6",
            ),
            DIV(
                INPUT(
                    _type="submit",
                    _value="Upload",
                    _style="padding:5px 15px",
                    _class="btn btn-primary",
                ),
                _class="col-sm-2",
            ),
            _class="row",
        )
    )

    def _format_error(lst):
        """['', 'afdskh'] --> '"","afdskh"'"""

        lst = [f'"{vl}"' for vl in lst]
        return ", ".join(lst)

    if form.accepts(request.vars):
        # get the data from the request, converting from uploaded bytes into StringIO
        data = io.StringIO(request.vars.myfile.value.decode("UTF-8-SIG"))
        data = csv.DictReader(data)

        # create an html upload report as the function runs
        html = ""

        # check the headers
        headers = data.fieldnames
        required = [
            "student_cid",
            "student_first_name",
            "student_last_name",
            "student_email",
            "course",
        ]

        missing_headers = set(required).difference(headers)

        if len(missing_headers) > 0:
            html = CAT(
                html,
                H2("Missing fields in file"),
                P(
                    "These fields are missing from the upload file: ",
                    ", ".join(missing_headers),
                ),
            )

            # Nothing is likely to work from this point, so bail early
            return dict(form=form, html=html, known_courses=known_courses)

        # extract the contents into a big list of dictionaries to work with
        # rather than having an iterator that runs through once
        data = [row for row in data]

        # Look for blank rows (all empty strings)
        blank = ["".join(row.values()) == "" for row in data]

        if sum(blank):
            html = CAT(
                html,
                H4("Blank lines"),
                P(f"The input file contains {sum(blank)} blank rows."),
            )

            data = [row for row, bl in zip(data, blank) if not bl]

        # - repackage the data into fields to do checks
        fields = {key: [item[key] for item in data] for key in headers}

        # - courses are recognized?
        unknown_courses = set(fields["course"]).difference(known_courses)

        if len(unknown_courses) > 0:
            html = CAT(
                html,
                H4("Unknown courses"),
                P("These courses are found in the file but are not recognized:"),
                P(_format_error(unknown_courses)),
                P("Valid values are: ", ", ".join(known_courses)),
            )

        # bad student emails
        bad_emails = [IS_EMAIL()(x) for x in fields["student_email"]]
        bad_emails = [x[0] for x in bad_emails if x[1] is not None]
        if len(bad_emails) > 0:
            html = CAT(
                html,
                H4("Invalid student emails"),
                P("The following are not well formatted emails: "),
                P(_format_error(set(bad_emails))),
            )

        # non numeric CID
        cids = set(fields["student_cid"])
        bad_cids = [x for x in cids if not x.isdigit()]
        if len(bad_cids) > 0:
            html = CAT(
                html,
                H4("Invalid student CID numbers"),
                P("The following are not valid CIDs: "),
                P(_format_error(set(bad_cids))),
            )

        # pre-existing CIDs
        existing_cids = db(db.students).select(db.students.student_cid)
        existing_cids = [v.student_cid for v in existing_cids]
        cids = set([int(v) for v in cids])

        bad_cids = cids.intersection(existing_cids)
        if len(bad_cids) > 0:
            html = CAT(
                html,
                H4("Invalid student CID numbers"),
                P("The following CIDs are already associated with students: "),
                P(_format_error(set(bad_cids))),
            )

        # empty names or just whitespace
        names = set(fields["student_first_name"] + fields["student_last_name"])
        bad_names = [x for x in names if x.isspace() or x == ""]

        if len(bad_names) > 0:
            html = CAT(
                html,
                H4("Invalid student names"),
                P(
                    "The student names data contains empty strings or "
                    "text just consisting of spaces"
                ),
            )

        # NOW insert students and create active student presentations.

        if html == "":
            for each_student in data:
                each_student["course"] = course_map[each_student["course"]]
                st_id = db.students.insert(**each_student)

                for stpres in active_pres_map[each_student["course"]]:
                    db.student_presentations.insert(
                        student=st_id,
                        course_presentation=stpres,
                        academic_year=CURRENT_PROJECT_YEAR,
                    )

            # load the assignments
            html = CAT(H2(str(len(data)) + " students successfully uploaded"))

    else:
        html = ""

    return dict(form=form, html=html, known_courses=known_courses)
