import os
import csv
import re
from timetable_functions import convert_date_to_weekdaytime

if db(db.auth_group).count() == 0:
    # Only one group to grant high level access
    db.auth_group.insert(role='admin', 
                         description='Module structure and sequences, courses, freezing')


if db(db.teaching_staff).count() == 0:
    
    filepath = os.path.join(request.folder, 'static', 'data', 'teaching_staff.csv')
    
    with open(filepath, encoding="utf8") as csvfile:
        db.teaching_staff.import_from_csv_file(csvfile)

if db(db.locations).count() == 0:
    
    filepath = os.path.join(request.folder, 'static', 'data', 'locations.csv')
    
    with open(filepath, encoding="utf8") as csvfile:
        db.locations.import_from_csv_file(csvfile)

if db(db.courses).count() == 0:
    
    filepath = os.path.join(request.folder, 'static', 'data', 'courses.csv')
    
    with open(filepath, encoding="utf8") as csvfile:
        db.courses.import_from_csv_file(csvfile)

if db(db.college_dates).count() == 0:
    
    filepath = os.path.join(request.folder, 'static', 'data', 'college_dates.csv')
    
    with open(filepath, encoding="utf8") as csvfile:
        db.college_dates.import_from_csv_file(csvfile)


if db(db.modules).count() == 0:
    
    # More complex as this needs to resolve the referencing of teaching
    # staff and the course ids from the original input. This file has a BOM
    # marker so needs a different encoding.
    
    filepath = os.path.join(request.folder, 'static', 'data', 'modules.csv')
    with open(filepath, encoding="utf-8-sig") as csvfile:
        
        reader = csv.DictReader(csvfile)
        
        # Convenor map
        convenors = db(db.teaching_staff).select()
        convenors = {c.firstname + ' ' + c.lastname: c.id for c in convenors}
        
        # Course map
        course_map = db(db.courses).select()
        course_map = {c.fullname: c.id for c in course_map}
        
        # Regex for course name keys
        course_regex = re.compile('^MSc|^MRes')
        
        for module in reader:
            # Find the convenor
            if module['Convenor'] in convenors:
                convenor_id = convenors[module['Convenor']]
            else:
                print(f"Unknown convenor: {module['Convenor']}")
                convenor_id = None
            
            # Package the courses
            courses = [ky for ky, vl in module.items() if course_regex.match(ky) and vl == '1']
            courses = [course_map[ky] for ky in courses]
            
            db.modules.insert(title=module['ModuleName'],
                                     convenor_id=convenor_id,
                                     description=module['Description'],
                                     aims=module['Aims'],
                                     reading=module['ReadingList'],
                                     other_notes=module['Additional'],
                                     exam_style=module['Exam Question Style Proposed By J&J'],
                                     courses=courses)


if db(db.module_events).count() == 0:
    
    # More complex as this needs to resolve the referencing of teaching
    # staff and module ids from the original input. This file has a BOM
    # marker so needs a different encoding.
    
    filepath = os.path.join(request.folder, 'static', 'data', 'module_events.csv')
    with open(filepath, encoding="utf-8-sig") as csvfile:
        
        reader = csv.DictReader(csvfile)
        
        # Teacher map
        teachers = db(db.teaching_staff).select()
        teachers = {c.firstname.lower() + ' ' + c.lastname.lower(): c.id for c in teachers}
        
        # Module map
        module_map = db(db.modules).select()
        module_map = {c.title: c.id for c in module_map}
        
        # lots of typos in modules, so use a mapping to correct
        module_filter = {
            "Actions": None,
            "Advanced Statistics": "Advanced statistics",
            "Behavioural Ecology": "Behavioural ecology",
            "Case Studies: Exploitation": None,
            "Case Studies: Invasive Species": None,
            "Case Studies: Protected Areas": None,
            "CMEE Miniproject: Intro, project selection and preliminary work	": "CMEE Miniproject: Intro, project selection and preliminary work",
            "Conservation Decision Making": "Conservation Decision-making",
            "Course Induction": None,
            "Durrell - Species declines and zoos": "Durrell",
            "Ecology and Global Change": "Ecology and global change",
            "Economics in Conservation": None, 
            "Environmental impact assessment": "Ecological Impact Assessment",
            "GIS/Stats/R": "Spatial Analyses and Geographic Information Systems (GIS)",
            "Graduate School Workshops": "Graduate School Workshop",
            "Introductio to Ecosystems and Environmental Change": None,
            "Introduction to Conservation Sciecne": None,
            "Introduction to EEC A": None,
            "Introduction to EEC B": None,
            "Introduction to EEC C": None,
            "Introduction to MRes EEC and EA": None,
            "Introduction to Tropical Forest Ecology": None,
            "Population ecology and quantiative genetics": "Population ecology and quantitative genetics",
            "Pro-network assessment": None,
            "Project preparation": None,
            "Science Communication": "Science communication",
            "Social Research Methods ": "Social Research Methods",
            "Social-ecological systems": "Social-Ecological Systems",
        }
        
        # Locations are a mess, so this mapping uses the original data values to 
        # map to a reconciled set and uses lists to combine location resources
        location_parse ={
            "CPB Seminar": ["CPB Seminar Room"],
            "CPB": ["CPB Seminar Room"],
            "Wallace": ["Wallace"],
            "Darwin": ["Darwin"],
            "Haldane": ["Haldane"],
            "Fisher": ["Fisher"],
            "Hamilton Computer Lab": ["Hamilton Computer Lab"],
            "Hamilton Field Lab": ["Hamilton Field Lab"],
            "Field lab": ["Hamilton Field Lab"],
            "Chobham Commons": ["Chobham Commons"],
            "Computer Room": ["Hamilton Computer Lab"],
            "CPB for CMEE and EEC (MRes) and Computer lab for all other courses": ["Hamilton Computer Lab", "CPB Seminar Room"],
            "Durrell Wildlife Conservation Trust": ["Durrell Wildlife Conservation Trust"],
            "Fisher/Haldane": ["Haldane","Fisher"],
            "Fisher/Haldane/Field lab": ["Haldane","Fisher", "Hamilton Field Lab"],
            "Fisher/Haldane/Wallace/CPB Seminar Room": ["Haldane","Fisher","Wallace","CPB Seminar Room"],
            "Hamilton Foyer": ["Hamilton Foyer"],
            "Kew": ["Kew Gardens"],
            "Kew Gardens": ["Kew Gardens"],
            "Lundy": ["Lundy"],
            "Malaysia": ["Malaysia"],
            "NHM": ["NHM"],
            "Offsite": ["Offsite"],
            "Seminar Room 1": ["Seminar Room 1"],
            "Seminar Room 2": ["Seminar Room 2"],
            "Silwood field and Hamilton Field Lab": ["Silwood Grounds", "Hamilton Field Lab"],
            "Silwood Grounds": ["Silwood Grounds"],
            "South Kensington": ["South Kensington"],
            "Tavern": ["Lundy Tavern"],
            "Wakehurst Place": ["Wakehurst Place"],
            "WTC": ["WTC"],
            "Zoological Society of London": ["Zoological Society of London"],
            "ZSL": ["Zoological Society of London"]}
        
        # Convert location map to db ids and hence to list format (|1|2|3|) for insertion
        for ky, vl in location_parse.items():
            rows = db(db.locations.title.belongs(vl)).select()
            #location_parse[ky] = '|' + '|'.join([str(r.id) for r in rows]) + '|'
            location_parse[ky] = [r.id for r in rows]

        for event in reader:
            
            # Find the teacher
            event_teacher = (event['LecturerFirstName'].strip().lower() 
                             + ' ' 
                             + event['LecturerLastName'].strip().lower())
            
            if event_teacher in teachers:
                teacher_id = teachers[event_teacher]
            else:
                print(f"Unknown event teacher: {event_teacher}")
                continue
            
            
            # Find the module - correct using the filter first
            if event['WeekName'] in module_filter and module_filter[event['WeekName']] is not None:
                event['WeekName'] =  module_filter[event['WeekName']]
            
            # Now look in the official list
            if event['WeekName'] in module_map:
                module_id = module_map[event['WeekName']]
            else:
                print(f"Unknown module: {event['WeekName']}")
                continue

            # Find the location
            if event['Location'] not in location_parse:
                print(f"Unknown location: {event['Location']}")
                location_id = None
            else:
                location_id = location_parse[event['Location']]
            
            # One odd thing about the original Excel source is that the dates
            # of the modules are only recorded at the event level - the date
            # can be seen in the timetable grid but isn't recorded. So here,
            # we use the event date to set the module week and then work out
            # everything from there
            
            module = db.modules[module_id]
            
            if module is not None:
                
                success, *event_data = convert_date_to_weekdaytime(event['StartDate'])
                
                if not success:
                    print(f"Failed to convert start date: {event['StartDate']}")
                    break
                
                evweek, evday, evtime = event_data
                
                # bring 2019 into 2020
                evweek = evweek if evweek > 0 else evweek + 52
                
                if module.module_week is None:
                    module.update_record(module_week = evweek)
                elif module.module_week != evweek:
                    print(f"Inconsistent module week within events: {event['LectureTitle']}")
                
                try:
                    db.module_events.insert(teacher_id=teacher_id,
                                        module_id=module_id,
                                        title=event['LectureTitle'],
                                        event_type=event['Type'],
                                        description=event['Description'],
                                        location_id=location_id,
                                        event_day=evday,
                                        start_time=event['StartTime'],
                                        duration=event['Length'])
                except:
                    sql = db.module_events._insert(teacher_id=teacher_id,
                                        module_id=module_id,
                                        title=event['LectureTitle'],
                                        event_type=event['Type'],
                                        description=event['Description'],
                                        location_id=location_id,
                                        event_day=evday,
                                        start_time=event['StartTime'],
                                        duration=event['Length'])
                    print(sql)
                    raise RuntimeError()

