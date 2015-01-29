from unittest import mock

from django.core.urlresolvers import reverse

from taiga.base.utils import json
from taiga.projects.tasks import services

from .. import factories as f

import pytest
pytestmark = pytest.mark.django_db


def test_get_tasks_from_bulk():
    data = """
Task #1
Task #2
"""
    tasks = services.get_tasks_from_bulk(data)

    assert len(tasks) == 2
    assert tasks[0].subject == "Task #1"
    assert tasks[1].subject == "Task #2"


def test_create_tasks_in_bulk(db):
    data = """
Task #1
Task #2
"""
    with mock.patch("taiga.projects.tasks.services.db") as db:
        tasks = services.create_tasks_in_bulk(data)
        db.save_in_bulk.assert_called_once_with(tasks, None, None)


def test_api_update_task_tags(client):
    task = f.create_task()
    f.MembershipFactory.create(project=task.project, user=task.owner, is_owner=True)
    url = reverse("tasks-detail", kwargs={"pk": task.pk})
    data = {"tags": ["back", "front"], "version": task.version}

    client.login(task.owner)
    response = client.json.patch(url, json.dumps(data))

    assert response.status_code == 200, response.data


def test_api_create_in_bulk_with_status(client):
    us = f.create_userstory()
    f.MembershipFactory.create(project=us.project, user=us.owner, is_owner=True)
    us.project.default_task_status = f.TaskStatusFactory.create(project=us.project)
    url = reverse("tasks-bulk-create")
    data = {
        "bulk_tasks": "Story #1\nStory #2",
        "us_id": us.id,
        "project_id": us.project.id,
        "sprint_id": us.milestone.id,
        "status_id": us.project.default_task_status.id
    }

    client.login(us.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200
    assert response.data[0]["status"] == us.project.default_task_status.id


def test_api_create_invalid_task(client):
    # Associated to a milestone and a user story.
    # But the User Story is not associated with the milestone
    us_milestone = f.MilestoneFactory.create()
    us = f.create_userstory(milestone=us_milestone)
    f.MembershipFactory.create(project=us.project, user=us.owner, is_owner=True)
    us.project.default_task_status = f.TaskStatusFactory.create(project=us.project)
    task_milestone = f.MilestoneFactory.create(project=us.project, owner=us.owner)

    url = reverse("tasks-list")
    data = {
        "user_story": us.id,
        "milestone": task_milestone.id,
        "subject": "Testing subject",
        "status": us.project.default_task_status.id,
        "project": us.project.id
    }

    client.login(us.owner)
    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400


def test_api_update_order_in_bulk(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_owner=True)
    task1 = f.create_task(project=project)
    task2 = f.create_task(project=project)

    url1 = reverse("tasks-bulk-update-taskboard-order")
    url2 = reverse("tasks-bulk-update-us-order")

    data = {
        "project_id": project.id,
        "bulk_tasks": [{"task_id": task1.id, "order": 1},
                         {"task_id": task2.id, "order": 2}]
    }

    client.login(project.owner)

    response1 = client.json.post(url1, json.dumps(data))
    response2 = client.json.post(url2, json.dumps(data))

    assert response1.status_code == 204, response1.data
    assert response2.status_code == 204, response2.data
