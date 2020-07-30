# Timetable help

This page provides an overview on how this system works and guidance on using it.

## Access

All of the information in this website is **publically visible**, mostly so that you don't have to log in to look things up. You will have to register, be approved, and then log in to make any edits. Some changes can only be made by a higher level admin user.

If you are logged in as a user, you can edit information in all modules and events: this is a collaborative data system!

_Although they can access it, this not intended to be a student-facing website - they should use the college calendars._


## Timings and dates

All module and event dates and times in this system are set as academic weeks and days relative to the **first day of autumn term**. This is stored in in the College Date table (see below). There should be no need to recalculate dates between years - changing this single date should bring everything across. Obviously, if module orders change then their data will need to be edited.

## Timetable database

The structure of the database is very like the old Excel workbook. It has seven tables that hold timetabling information.

* **Locations**: This currently simply maintains a list of location names. It may be expanded to include CELCAT identifiers and other information. Any user can add a new location if needed, but do look through first to see if the location is under a different name (e.g. `Computer Room` = `Hamilton Computer Lab`)

* **Teaching Staff**: A simple table list of anyone convening a course or module or running a teaching event. Again, it might be extended to hold CELCAT information.  Any user can add a new member of staff if needed.

* **College Dates**: This table contains all the college dates for the academic year. It does need to be updated for each fresh academic year. It contains the all important reference date: **first day of autumn term**.  Only the admin user can edit this table. 

* **Recurring Events**: This is extremely similar to College Dates - it should be used to add in recurring events outside of the course modules, such as seminar series and Wednesday pm club and sports times.  Only the admin user can edit this table. 

* **Courses**: This is the master list of courses in the system. It contains the course name, abbreviation and course convenors.  Only the admin user can edit this table. 

* **Modules**: This table contains the modules taught in a course or set of courses. This is basically any thematically linked set of _events_. It records the course convenors, higher level information about the module (description, aims etc) and which courses take the module. 

    If a module has any associated events, then the start and end of the module will be taken from that set of events, but the module table can also hold a placeholder week and duration so that modules can be displayed in calendar views before events are added.

    There is an option to represent a module as a **series module**. This is intended to separate out themed teaching that stretches out through the year, such as workshops or reading groups. Series modules are not shown in the module grid to keep the format clean and are shown separately in the course view pages and in course documents.  

* **Events**: These are the actual individual teaching events. Each event is associated with a single module and the table also holds an event teacher, a title and description and a location. You can also set which courses attending the module should attend a specific event - this can be used to filter a module description down for a course.

## Hiding data

Courses, modules and events can all be hidden - although only an admin can hide a course. This allows us to keep data in the system but switch components from year to year.










 