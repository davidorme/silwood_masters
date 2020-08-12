# Silwood Masters Report Marking web application

## Design notes

### Previous system

This web application is designed to bring together parts of previously separate automated systems into a single, user friendly interface. Previously, there were the following components:

1.  A command line Python script that put together a set of web links to some Google Drive forms. These were quite long complicated links used to partly populate the form with student details and the marker details. It took a CSV file of assignments details as an input.

2.  A pair of Google Drive forms, one each for the EEC Supervisor and Marker form styles. Markers and supervisors came to these sheets from emailed links and once they were filled in and submitted, the information was saved automatically in a Google Sheet, using built in Google Form functionality. Issue with this were:

    * Every new form needs a new Form, a new connected Sheet and independent processing: it is not easily extendable.
    * Because the forms are populated by the links, it is possible for users to edit student details. They're really not meant to change the pre-populated data but the sometimes did.

3. The Google Sheets were set up to use a script extension called 'autocrat', which loaded the submitted data into a template, turned that into a PDF and emailed it to the marker, as well as storing it on the Google Drive. This mostly worked well, but was incompatible with people filtering a sheet and often broke with annual script updates and changes in the Google API. 

4.  A Python script could then be run on a finished set of reports to check marking reports for students, strip out the pages with confidential information and collate a public PDF to send to students. This wasn't particularly smart - it only stripped off the last page, so it needed manually checking in case someone had written a diatribe in the private comments.

5.  A final Python script could be used to automail these reports (and grades) to students.

All well and good, but not great to use unless you'd written it and knew how it worked.

### New system

The aim of this system is to reduce the number of steps and provide a more user-friendly UI for course coordinators.

1.  Assignments are created and entered into a database, either through a friendly one at a time web form or by bulk upload from a CSV file, similar to the previous starting point. These are now fixed, so a marker can be sent a link to a form which has locked student information, and can only use the form to provide a single report. 

    This also means that it is easy to have a single unified page that shows the complete set of expected marking assignments and to show their current status. This allows coordinators to monitor marking progress and easily chase down late reports etc. This page is currently only visible to logged in course administrators and also provides simple actions to: **distribute marking** to markers, **release reports** to students, **download PDFs** and **download grades** in an Excel file. This is only accessible to registered users.

2.  Form styles and data are defined using JSON files (see below). The file will contain the layout, instructions and questions for a form and define a set of variables, associated with web form inputs, that are the form data. The JSON allows both web forms and report PDFs to be generated on the fly, and the data entered by markers is stored in the single assignements table as a JSON object. A simple pairing of course presentation and marker role pairs a particular assignment to a particular form JSON. This allows new forms to be cleanly added.

3.  Access control is by UUID security token: in order to either access a marking report or download a PDF, you need the right combination of marking record ID number (which isn't hard to search) and random UUID token (which _is_!). Two tokens provide **staff access** for writing reports and downloading full report PDFs and **public access** for students to download reports excluding any confidential report questions.

### Form design 

The following describes the JSON structure used to describe forms:

At the highest level:

    {"title":"A heading at the top of the report webpage",
    "pdftitle":"A heading at the top of the PDF report",
    "instructions":"HTML marked up text explaining how to <strong>use the marking form</strong>",
    "questions":[ {question object 1}, {question object 2}, ...]}

Question objects have the following structure:

    {"title":"A title to appear above a question block",
     "confidential": A boolean true or false: any question with confidential set to true will not appear in public reports ,
     "components":[ {question component 1}, {question component 2}, ...]},

Question component objects can be of three types: `rubric`, `comment` or `select`.  All three must contain a `type`, a name for the `variable` under which the marking data will be stored within the JSON data field in the database, a short text `label` that will appear to the left of the component in the webform or PDF report and a boolean `required` that tells the application which variables have to be provided before a user can submit a form.

#### Rubric type 

Rubric components also need to provide an array of `options`, which are used to create and label a horizontal set of radio buttons. It probably isn't sensible to have more than five options! An example rubric component is:

    {"type":"rubric",
     "variable":"presentation_rubric",
     "label":"Rubric",
     "options":["Messy", "Below Average", "Average", "Above Average", "Publication Standard"],
     "required":true}

#### Comment type 

Comment types just have some simple formatting options: `nrow` tells the web form how many tall a text box to use  - the default is rather tall - and `placeholder` sets some greyed out placeholder text in the box before a user starts typing in it. An example comment component is:

    {"type":"comment",
     "variable":"presentation_comments",
     "label":"Comment",
     "nrow": 2,
     "placeholder":"Optional comments",
     "required":false}


#### Select component 

Like the rubric component, this requires an array of `options`, which are used to populate a dropdown menu. This can be used to provide a wider set of options, such as for a grade selection:

    {"type":"select",
     "variable":"grade",
     "label":"Select a grade",
     "options":["100% (A*)", "95% (A*)", "90% (A*)", "85% (A*)",
                "80% (A)", "76% (A)", "72% (A)",
                "68% (B)", "65% (B)", "62% (B)",
                "58% (C)", "55% (C)", "52% (C)",
                "48% (D)", "45% (D)", "42% (D)", "35% (D)", "30% (D)", "25% (D)", 
                "20% (D)", "15% (D)", "10% (D)", "5% (D)", "0% (D)"],
     "required":true}
  