from models.deployment_options import DeploymentOptions


def test_deployment_options_normalizes_values():
    options = DeploymentOptions(
        description="  Campagne nationale  ",
        assigned_to="  user-123  ",
    )

    assert options.description == "Campagne nationale"
    assert options.assigned_to == "user-123"


def test_deployment_options_accepts_unassigned_project():
    options = DeploymentOptions(
        description=" ",
        assigned_to=" ",
    )

    assert options.description == ""
    assert options.assigned_to is None