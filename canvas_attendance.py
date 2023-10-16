#!/usr/bin/env python3

import sys, os, csv, yaml
from argparse import ArgumentParser
from canvasapi import Canvas
from pprint import pprint

def yml_parse(path):
    with open(path, 'r') as stream:
        data_loaded = yaml.load(stream)
        return data_loaded
    return None

def acadly_key(first, last):
    return first + ' ' + last

if __name__ == '__main__':
    SCRIPTPATH = os.path.dirname(os.path.abspath(__file__))

    parser = ArgumentParser(description='Upload Acadly data to canvas')
    parser.add_argument("--config", type=str,
        dest='config', required=True,
        help="Path to YAML config file")
    parser.add_argument("--acadly", metavar='PATH', type=str, nargs='+',
        dest='attendance', default=None, required=True,
        help="path to CSV attendance files from Acadly.")
    parser.add_argument("--gradebook", metavar='PATH', type=str,
        dest='gradebook', default=None, required=False,
        help="Canvas Gradebook CSV holding student names")
    parser.add_argument("--roster", metavar='PATH', type=str,
        dest='roster', default=None, required=True,
        help="Annotated Roster CSV holding Acadly/Canvas userids")

    OPT = vars(parser.parse_args())

    # get options from the yml config file
    try:
        with open(OPT['config'], 'r') as file:
            config = yaml.load(file)
            OPT.update(config)
    except yaml.YAMLError as e:
        print("Error in configuration file:", e)

    scores = {}
    with open(OPT['roster'], 'r') as csvfile:
        for r in csv.DictReader(csvfile):
            k = acadly_key(r['Acadly First'], r['Acadly Last'])
            scores[k] = {
                'Student':r['Student'],
                'ID':r['ID'],
                'Score':0, }

    for f in OPT['attendance']:
        with open(f, 'r') as csvfile:
            for i in range(9):
                next(csvfile)
            reader = csv.DictReader(csvfile)
            for r in reader:
                k = acadly_key(r['Student Given Name'], r['Student Family Name'])
                if not k in scores.keys():
                    print("WARNING:", k, "not in roster")
                    continue
                if r['Status'] == 'Present':
                    scores[k]['Score'] += 1

    for k in scores.keys():
        print(scores[k]['Score'], '\t', scores[k]['Student'])

    pprint(OPT)

    canvas = Canvas(OPT['API_URL'], OPT['API_KEY'])
    course = canvas.get_course(OPT['COURSE_ID'])
    assignment = course.get_assignment(OPT['ASSIGNMENT_ID'])
    print("Uploading score data for Assignment", assignment, "for", course.name)

    assignment = assignment.edit(assignment={'muted' : True})
    print("Muted assignment")

    for k in scores.keys():
        sid = scores[k]['ID']
        print("For student '"+scores[k]['Student']+"'", "("+sid+")")
        submission = assignment.get_submission(sid)

        print("\t Setting score:", scores[k]['Score'])
        result = submission.edit(submission={'posted_grade': scores[k]['Score']})
        if not result:
            print("Failed to set grade", file=sys.stderr)
            exit(1)
