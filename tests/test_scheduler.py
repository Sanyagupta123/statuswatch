from unittest.mock import Mock

from statuswatch.scheduler import schedule_monitor


def test_scheduler_job_uses_monitor_interval_and_prevents_overlap():
    scheduler=Mock()
    scheduler.get_job.return_value=None
    schedule_monitor(scheduler,{"id":3,"interval_seconds":45})
    args=scheduler.add_job.call_args
    assert args.args[1]=="interval"
    assert args.kwargs["seconds"]==45
    assert args.kwargs["max_instances"]==1
