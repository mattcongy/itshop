# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2016 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2016 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2016 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# Copyright (C) 2014-2016 Anler Hernández <hello@anler.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import uuid
import csv
import pytz

from datetime import datetime, timedelta
from urllib.parse import quote

from unittest import mock

from django.core.urlresolvers import reverse

from taiga.base.utils import json
from taiga.permissions.choices import MEMBERS_PERMISSIONS, ANON_PERMISSIONS
from taiga.projects.issues import services, models
from taiga.projects.occ import OCCResourceMixin

from .. import factories as f

import pytest
pytestmark = pytest.mark.django_db


def test_get_issues_from_bulk():
    data = """
Issue #1
Issue #2
"""
    issues = services.get_issues_from_bulk(data)

    assert len(issues) == 2
    assert issues[0].subject == "Issue #1"
    assert issues[1].subject == "Issue #2"


def test_create_issues_in_bulk(db):
    data = """
Issue #1
Issue #2
"""

    with mock.patch("taiga.projects.issues.services.db") as db:
        issues = services.create_issues_in_bulk(data)
        db.save_in_bulk.assert_called_once_with(issues, None, None)


def test_create_issue_without_status(client):
    user = f.UserFactory.create()
    project = f.ProjectFactory.create(owner=user)
    status = f.IssueStatusFactory.create(project=project)
    priority = f.PriorityFactory.create(project=project)
    severity = f.SeverityFactory.create(project=project)
    type = f.IssueTypeFactory.create(project=project)
    project.default_issue_status = status
    project.default_priority = priority
    project.default_severity = severity
    project.default_issue_type = type
    project.save()
    f.MembershipFactory.create(project=project, user=user, is_admin=True)
    url = reverse("issues-list")

    data = {"subject": "Test user story", "project": project.id}
    client.login(user)
    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 201
    assert response.data['status'] == project.default_issue_status.id
    assert response.data['severity'] == project.default_severity.id
    assert response.data['priority'] == project.default_priority.id
    assert response.data['type'] == project.default_issue_type.id


def test_create_issue_without_status_in_project_without_default_values(client):
    user = f.UserFactory.create()
    project = f.ProjectFactory.create(owner=user,
                                      default_issue_status=None,
                                      default_priority=None,
                                      default_severity=None,
                                      default_issue_type = None)

    f.MembershipFactory.create(project=project, user=user, is_admin=True)
    url = reverse("issues-list")

    data = {"subject": "Test user story", "project": project.id}
    client.login(user)
    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 201
    assert response.data['status'] == None
    assert response.data['severity'] == None
    assert response.data['priority'] == None
    assert response.data['type'] == None


def test_api_create_issues_in_bulk(client):
    project = f.create_project()
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("issues-bulk-create")

    data = {"bulk_issues": "Issue #1\nIssue #2\n",
            "project_id": project.id}

    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200, response.data


def test_api_filter_by_subject(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="some random subject", owner=user)
    url = reverse("issues-list") + "?q=some subject"

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1, number_of_issues


def test_api_filter_by_text_1(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="this is the issue one", owner=user)
    f.create_issue(subject="this is the issue two", owner=issue.owner)
    url = reverse("issues-list") + "?q=one"

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1


def test_api_filter_by_text_2(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="this is the issue one", owner=user)
    f.create_issue(subject="this is the issue two", owner=issue.owner)
    url = reverse("issues-list") + "?q=this is the issue one"

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1


def test_api_filter_by_text_3(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="this is the issue one", owner=user)
    f.create_issue(subject="this is the issue two", owner=issue.owner)
    url = reverse("issues-list") + "?q=this is the issue"

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 2


def test_api_filter_by_text_4(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="this is the issue one", owner=user)
    f.create_issue(subject="this is the issue two", owner=issue.owner)
    url = reverse("issues-list") + "?q=one two"

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 0


def test_api_filter_by_text_5(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="python 3", owner=user)
    url = reverse("issues-list") + "?q=python 3"

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1


def test_api_filter_by_text_6(client):
    user = f.UserFactory(is_superuser=True)
    f.create_issue(owner=user)
    issue = f.create_issue(subject="test", owner=user)
    issue.ref = 123
    issue.save()
    url = reverse("issues-list") + "?q=%s" % (issue.ref)

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1


def test_api_filter_by_created_date(client):
    user = f.UserFactory(is_superuser=True)
    one_day_ago = datetime.now(pytz.utc) - timedelta(days=1)

    old_issue = f.create_issue(owner=user, created_date=one_day_ago)
    issue = f.create_issue(owner=user)

    url = reverse("issues-list") + "?created_date=%s" % (
        quote(issue.created_date.isoformat())
    )

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1
    assert response.data[0]["ref"] == issue.ref


def test_api_filter_by_created_date__gt(client):
    user = f.UserFactory(is_superuser=True)
    one_day_ago = datetime.now(pytz.utc) - timedelta(days=1)

    old_issue = f.create_issue(owner=user, created_date=one_day_ago)
    issue = f.create_issue(owner=user)

    url = reverse("issues-list") + "?created_date__gt=%s" % (
        quote(one_day_ago.isoformat())
    )

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1
    assert response.data[0]["ref"] == issue.ref


def test_api_filter_by_created_date__gte(client):
    user = f.UserFactory(is_superuser=True)
    one_day_ago = datetime.now(pytz.utc) - timedelta(days=1)

    old_issue = f.create_issue(owner=user, created_date=one_day_ago)
    issue = f.create_issue(owner=user)

    url = reverse("issues-list") + "?created_date__gte=%s" % (
        quote(one_day_ago.isoformat())
    )

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 2


def test_api_filter_by_created_date__lt(client):
    user = f.UserFactory(is_superuser=True)
    one_day_ago = datetime.now(pytz.utc) - timedelta(days=1)

    old_issue = f.create_issue(owner=user, created_date=one_day_ago)
    issue = f.create_issue(owner=user)

    url = reverse("issues-list") + "?created_date__lt=%s" % (
        quote(issue.created_date.isoformat())
    )

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert response.data[0]["ref"] == old_issue.ref


def test_api_filter_by_created_date__lte(client):
    user = f.UserFactory(is_superuser=True)
    one_day_ago = datetime.now(pytz.utc) - timedelta(days=1)

    old_issue = f.create_issue(owner=user, created_date=one_day_ago)
    issue = f.create_issue(owner=user)

    url = reverse("issues-list") + "?created_date__lte=%s" % (
        quote(issue.created_date.isoformat())
    )

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 2


def test_api_filter_by_modified_date__gte(client):
    user = f.UserFactory(is_superuser=True)
    _day_ago = datetime.now(pytz.utc) - timedelta(days=1)

    older_issue = f.create_issue(owner=user)
    issue = f.create_issue(owner=user)
    # we have to refresh as it slightly differs
    issue.refresh_from_db()

    assert older_issue.modified_date < issue.modified_date

    url = reverse("issues-list") + "?modified_date__gte=%s" % (
        quote(issue.modified_date.isoformat())
    )

    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1
    assert response.data[0]["ref"] == issue.ref


def test_api_filter_by_finished_date(client):
    user = f.UserFactory(is_superuser=True)
    project = f.ProjectFactory.create()
    status0 = f.IssueStatusFactory.create(project=project, is_closed=True)

    issue = f.create_issue(owner=user)
    finished_issue = f.create_issue(owner=user, status=status0)

    assert finished_issue.finished_date

    url = reverse("issues-list") + "?finished_date__gte=%s" % (
        quote(finished_issue.finished_date.isoformat())
    )
    client.login(issue.owner)
    response = client.get(url)
    number_of_issues = len(response.data)

    assert response.status_code == 200
    assert number_of_issues == 1
    assert response.data[0]["ref"] == finished_issue.ref


def test_api_filters_data(client):
    project = f.ProjectFactory.create()
    user1 = f.UserFactory.create(is_superuser=True)
    f.MembershipFactory.create(user=user1, project=project)
    user2 = f.UserFactory.create(is_superuser=True)
    f.MembershipFactory.create(user=user2, project=project)
    user3 = f.UserFactory.create(is_superuser=True)
    f.MembershipFactory.create(user=user3, project=project)

    status0 = f.IssueStatusFactory.create(project=project)
    status1 = f.IssueStatusFactory.create(project=project)
    status2 = f.IssueStatusFactory.create(project=project)
    status3 = f.IssueStatusFactory.create(project=project)

    type1 = f.IssueTypeFactory.create(project=project)
    type2 = f.IssueTypeFactory.create(project=project)

    severity0 = f.SeverityFactory.create(project=project)
    severity1 = f.SeverityFactory.create(project=project)
    severity2 = f.SeverityFactory.create(project=project)
    severity3 = f.SeverityFactory.create(project=project)

    priority0 = f.PriorityFactory.create(project=project)
    priority1 = f.PriorityFactory.create(project=project)
    priority2 = f.PriorityFactory.create(project=project)
    priority3 = f.PriorityFactory.create(project=project)

    tag0 = "test1test2test3"
    tag1 = "test1"
    tag2 = "test2"
    tag3 = "test3"

    # ------------------------------------------------------------------------------------------------
    # | Issue |  Owner | Assigned To | Status  | Type  | Priority  | Severity  | Tags                |
    # |-------#--------#-------------#---------#-------#-----------#-----------#---------------------|
    # | 0     |  user2 | None        | status3 | type1 | priority2 | severity1 |      tag1           |
    # | 1     |  user1 | None        | status3 | type2 | priority2 | severity1 |           tag2      |
    # | 2     |  user3 | None        | status1 | type1 | priority3 | severity2 |      tag1 tag2      |
    # | 3     |  user2 | None        | status0 | type2 | priority3 | severity1 |                tag3 |
    # | 4     |  user1 | user1       | status0 | type1 | priority2 | severity3 |      tag1 tag2 tag3 |
    # | 5     |  user3 | user1       | status2 | type2 | priority3 | severity2 |                tag3 |
    # | 6     |  user2 | user1       | status3 | type1 | priority2 | severity0 |      tag1 tag2      |
    # | 7     |  user1 | user2       | status0 | type2 | priority1 | severity3 |                tag3 |
    # | 8     |  user3 | user2       | status3 | type1 | priority0 | severity1 |      tag1           |
    # | 9     |  user2 | user3       | status1 | type2 | priority0 | severity2 | tag0                |
    # ------------------------------------------------------------------------------------------------

    issue0 = f.IssueFactory.create(project=project, owner=user2, assigned_to=None,
                                   status=status3, type=type1, priority=priority2, severity=severity1,
                                   tags=[tag1])
    issue1 = f.IssueFactory.create(project=project, owner=user1, assigned_to=None,
                                   status=status3, type=type2, priority=priority2, severity=severity1,
                                   tags=[tag2])
    issue2 = f.IssueFactory.create(project=project, owner=user3, assigned_to=None,
                                   status=status1, type=type1, priority=priority3, severity=severity2,
                                   tags=[tag1, tag2])
    issue3 = f.IssueFactory.create(project=project, owner=user2, assigned_to=None,
                                   status=status0, type=type2, priority=priority3, severity=severity1,
                                   tags=[tag3])
    issue4 = f.IssueFactory.create(project=project, owner=user1, assigned_to=user1,
                                   status=status0, type=type1, priority=priority2, severity=severity3,
                                   tags=[tag1, tag2, tag3])
    issue5 = f.IssueFactory.create(project=project, owner=user3, assigned_to=user1,
                                   status=status2, type=type2, priority=priority3, severity=severity2,
                                   tags=[tag3])
    issue6 = f.IssueFactory.create(project=project, owner=user2, assigned_to=user1,
                                   status=status3, type=type1, priority=priority2, severity=severity0,
                                   tags=[tag1, tag2])
    issue7 = f.IssueFactory.create(project=project, owner=user1, assigned_to=user2,
                                   status=status0, type=type2, priority=priority1, severity=severity3,
                                   tags=[tag3])
    issue8 = f.IssueFactory.create(project=project, owner=user3, assigned_to=user2,
                                   status=status3, type=type1, priority=priority0, severity=severity1,
                                   tags=[tag1])
    issue9 = f.IssueFactory.create(project=project, owner=user2, assigned_to=user3,
                                   status=status1, type=type2, priority=priority0, severity=severity2,
                                   tags=[tag0])

    url = reverse("issues-filters-data") + "?project={}".format(project.id)

    client.login(user1)

    ## No filter
    response = client.get(url)
    assert response.status_code == 200

    assert next(filter(lambda i: i['id'] == user1.id, response.data["owners"]))["count"] == 3
    assert next(filter(lambda i: i['id'] == user2.id, response.data["owners"]))["count"] == 4
    assert next(filter(lambda i: i['id'] == user3.id, response.data["owners"]))["count"] == 3

    assert next(filter(lambda i: i['id'] == None, response.data["assigned_to"]))["count"] == 4
    assert next(filter(lambda i: i['id'] == user1.id, response.data["assigned_to"]))["count"] == 3
    assert next(filter(lambda i: i['id'] == user2.id, response.data["assigned_to"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == user3.id, response.data["assigned_to"]))["count"] == 1

    assert next(filter(lambda i: i['id'] == status0.id, response.data["statuses"]))["count"] == 3
    assert next(filter(lambda i: i['id'] == status1.id, response.data["statuses"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == status2.id, response.data["statuses"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == status3.id, response.data["statuses"]))["count"] == 4

    assert next(filter(lambda i: i['id'] == type1.id, response.data["types"]))["count"] == 5
    assert next(filter(lambda i: i['id'] == type2.id, response.data["types"]))["count"] == 5

    assert next(filter(lambda i: i['id'] == priority0.id, response.data["priorities"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == priority1.id, response.data["priorities"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == priority2.id, response.data["priorities"]))["count"] == 4
    assert next(filter(lambda i: i['id'] == priority3.id, response.data["priorities"]))["count"] == 3

    assert next(filter(lambda i: i['id'] == severity0.id, response.data["severities"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == severity1.id, response.data["severities"]))["count"] == 4
    assert next(filter(lambda i: i['id'] == severity2.id, response.data["severities"]))["count"] == 3
    assert next(filter(lambda i: i['id'] == severity3.id, response.data["severities"]))["count"] == 2

    assert next(filter(lambda i: i['name'] == tag0, response.data["tags"]))["count"] == 1
    assert next(filter(lambda i: i['name'] == tag1, response.data["tags"]))["count"] == 5
    assert next(filter(lambda i: i['name'] == tag2, response.data["tags"]))["count"] == 4
    assert next(filter(lambda i: i['name'] == tag3, response.data["tags"]))["count"] == 4

    ## Filter ((status0 or status3) and type1)
    response = client.get(url + "&status={},{}&type={}".format(status3.id, status0.id, type1.id))
    assert response.status_code == 200

    assert next(filter(lambda i: i['id'] == user1.id, response.data["owners"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == user2.id, response.data["owners"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == user3.id, response.data["owners"]))["count"] == 1

    assert next(filter(lambda i: i['id'] == None, response.data["assigned_to"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == user1.id, response.data["assigned_to"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == user2.id, response.data["assigned_to"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == user3.id, response.data["assigned_to"]))["count"] == 0

    assert next(filter(lambda i: i['id'] == status0.id, response.data["statuses"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == status1.id, response.data["statuses"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == status2.id, response.data["statuses"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == status3.id, response.data["statuses"]))["count"] == 3

    assert next(filter(lambda i: i['id'] == type1.id, response.data["types"]))["count"] == 4
    assert next(filter(lambda i: i['id'] == type2.id, response.data["types"]))["count"] == 3

    assert next(filter(lambda i: i['id'] == priority0.id, response.data["priorities"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == priority1.id, response.data["priorities"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == priority2.id, response.data["priorities"]))["count"] == 3
    assert next(filter(lambda i: i['id'] == priority3.id, response.data["priorities"]))["count"] == 0

    assert next(filter(lambda i: i['id'] == severity0.id, response.data["severities"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == severity1.id, response.data["severities"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == severity2.id, response.data["severities"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == severity3.id, response.data["severities"]))["count"] == 1

    assert next(filter(lambda i: i['name'] == tag0, response.data["tags"]))["count"] == 0
    assert next(filter(lambda i: i['name'] == tag1, response.data["tags"]))["count"] == 4
    assert next(filter(lambda i: i['name'] == tag2, response.data["tags"]))["count"] == 2
    assert next(filter(lambda i: i['name'] == tag3, response.data["tags"]))["count"] == 1

    ## Filter ((tag1 and tag2) and (user1 or user2))
    response = client.get(url + "&tags={},{}&owner={},{}".format(tag1, tag2, user1.id, user2.id))
    assert response.status_code == 200

    assert next(filter(lambda i: i['id'] == user1.id, response.data["owners"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == user2.id, response.data["owners"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == user3.id, response.data["owners"]))["count"] == 1

    assert next(filter(lambda i: i['id'] == None, response.data["assigned_to"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == user1.id, response.data["assigned_to"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == user2.id, response.data["assigned_to"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == user3.id, response.data["assigned_to"]))["count"] == 0

    assert next(filter(lambda i: i['id'] == status0.id, response.data["statuses"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == status1.id, response.data["statuses"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == status2.id, response.data["statuses"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == status3.id, response.data["statuses"]))["count"] == 1

    assert next(filter(lambda i: i['id'] == type1.id, response.data["types"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == type2.id, response.data["types"]))["count"] == 0

    assert next(filter(lambda i: i['id'] == priority0.id, response.data["priorities"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == priority1.id, response.data["priorities"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == priority2.id, response.data["priorities"]))["count"] == 2
    assert next(filter(lambda i: i['id'] == priority3.id, response.data["priorities"]))["count"] == 0

    assert next(filter(lambda i: i['id'] == severity0.id, response.data["severities"]))["count"] == 1
    assert next(filter(lambda i: i['id'] == severity1.id, response.data["severities"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == severity2.id, response.data["severities"]))["count"] == 0
    assert next(filter(lambda i: i['id'] == severity3.id, response.data["severities"]))["count"] == 1

    assert next(filter(lambda i: i['name'] == tag0, response.data["tags"]))["count"] == 0
    assert next(filter(lambda i: i['name'] == tag1, response.data["tags"]))["count"] == 2
    assert next(filter(lambda i: i['name'] == tag2, response.data["tags"]))["count"] == 2
    assert next(filter(lambda i: i['name'] == tag3, response.data["tags"]))["count"] == 1


def test_get_invalid_csv(client):
    url = reverse("issues-csv")

    response = client.get(url)
    assert response.status_code == 404

    response = client.get("{}?uuid={}".format(url, "not-valid-uuid"))
    assert response.status_code == 404


def test_get_valid_csv(client):
    url = reverse("issues-csv")
    project = f.ProjectFactory.create(issues_csv_uuid=uuid.uuid4().hex)

    response = client.get("{}?uuid={}".format(url, project.issues_csv_uuid))
    assert response.status_code == 200


def test_custom_fields_csv_generation():
    project = f.ProjectFactory.create(issues_csv_uuid=uuid.uuid4().hex)
    attr = f.IssueCustomAttributeFactory.create(project=project, name="attr1", description="desc")
    issue = f.IssueFactory.create(project=project)
    attr_values = issue.custom_attributes_values
    attr_values.attributes_values = {str(attr.id):"val1"}
    attr_values.save()
    queryset = project.issues.all()
    data = services.issues_to_csv(project, queryset)
    data.seek(0)
    reader = csv.reader(data)
    row = next(reader)
    assert row[23] == attr.name
    row = next(reader)
    assert row[23] == "val1"


def test_api_validator_assigned_to_when_update_issues(client):
    project = f.create_project(anon_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                               public_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)))
    project_member_owner = f.MembershipFactory.create(project=project,
                                                      user=project.owner,
                                                      is_admin=True,
                                                      role__project=project,
                                                      role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    project_member = f.MembershipFactory.create(project=project,
                                                is_admin=True,
                                                role__project=project,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    project_no_member = f.MembershipFactory.create(is_admin=True)

    issue = f.create_issue(project=project, owner=project.owner)

    url = reverse('issues-detail', kwargs={"pk": issue.pk})

    # assign
    data = {
        "assigned_to": project_member.user.id,
    }

    with mock.patch.object(OCCResourceMixin, "_validate_and_update_version"):
        client.login(project.owner)

        response = client.json.patch(url, json.dumps(data))
        assert response.status_code == 200, response.data
        assert "assigned_to" in response.data
        assert response.data["assigned_to"] == project_member.user.id

    # unassign
    data = {
        "assigned_to": None,
    }

    with mock.patch.object(OCCResourceMixin, "_validate_and_update_version"):
        client.login(project.owner)

        response = client.json.patch(url, json.dumps(data))
        assert response.status_code == 200, response.data
        assert "assigned_to" in response.data
        assert response.data["assigned_to"] == None

    # assign to invalid user
    data = {
        "assigned_to": project_no_member.user.id,
    }

    with mock.patch.object(OCCResourceMixin, "_validate_and_update_version"):
        client.login(project.owner)

        response = client.json.patch(url, json.dumps(data))
        assert response.status_code == 400, response.data


def test_api_validator_assigned_to_when_create_issues(client):
    project = f.create_project(anon_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                               public_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)))
    project_member_owner = f.MembershipFactory.create(project=project,
                                                      user=project.owner,
                                                      is_admin=True,
                                                      role__project=project,
                                                      role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    project_member = f.MembershipFactory.create(project=project,
                                                is_admin=True,
                                                role__project=project,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    project_no_member = f.MembershipFactory.create(is_admin=True)

    url = reverse('issues-list')

    # assign
    data = {
        "subject": "test",
        "project": project.id,
        "assigned_to": project_member.user.id,
    }

    with mock.patch.object(OCCResourceMixin, "_validate_and_update_version"):
        client.login(project.owner)

        response = client.json.post(url, json.dumps(data))
        assert response.status_code == 201, response.data
        assert "assigned_to" in response.data
        assert response.data["assigned_to"] == project_member.user.id

    # unassign
    data = {
        "subject": "test",
        "project": project.id,
        "assigned_to": None,
    }

    with mock.patch.object(OCCResourceMixin, "_validate_and_update_version"):
        client.login(project.owner)

        response = client.json.post(url, json.dumps(data))
        assert response.status_code == 201, response.data
        assert "assigned_to" in response.data
        assert response.data["assigned_to"] == None

    # assign to invalid user
    data = {
        "subject": "test",
        "project": project.id,
        "assigned_to": project_no_member.user.id,
    }

    with mock.patch.object(OCCResourceMixin, "_validate_and_update_version"):
        client.login(project.owner)

        response = client.json.post(url, json.dumps(data))
        assert response.status_code == 400, response.data
