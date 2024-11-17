from unittest import TestCase

from bam_app.models.task_queue import TaskQueue


class TestTaskQueue(TestCase):
    def test_add_task(self):
        task = TaskQueue.add_task(
            session=None, task_name="test_task", user_id=1
        )
        self.assertEqual(task.task_name, "test_task")
        self.assertEqual(task.user_id, 1)
        self.assertEqual(task.status, "queued")

    def test_pop_task(self):
        task = TaskQueue.add_task(
            session=None, task_name="test_task", user_id=1
        )
        task = TaskQueue.pop_task(session=None)
        self.assertEqual(task.status, "running")

    def test_update_task_status(self):
        task = TaskQueue.add_task(
            session=None, task_name="test_task", user_id=1
        )
        TaskQueue.update_task_status(
            session=None, task_id=task.id, status="success"
        )
        self.assertEqual(task.status, "success")
