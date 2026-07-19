from unittest.mock import patch

import main


def test_activity_data_uses_local_health_without_calling_strava():
    local = ({"source": "healthfit/apple-health"}, {"ytd_run_totals": {}}, [{"type": "Run"}], None)
    with patch.object(main, "get_local_health_data", return_value=local) as local_loader, \
         patch.object(main, "get_strava_data") as strava_loader:
        result = main.get_activity_data()

    assert result == local
    local_loader.assert_called_once_with()
    strava_loader.assert_not_called()
