from backend.app.core.roles import Permission, Role, has_permission


def test_admin_has_every_permission():
    assert all(has_permission(Role.ADMIN, permission) for permission in Permission)


def test_commercial_cannot_read_all_prospects_or_manage_users():
    assert has_permission(Role.COMMERCIAL, Permission.PROSPECT_READ_ASSIGNED)
    assert not has_permission(Role.COMMERCIAL, Permission.PROSPECT_READ_ALL)
    assert not has_permission(Role.COMMERCIAL, Permission.USER_MANAGE)


def test_trainer_has_minimal_foundation_permissions():
    assert has_permission(Role.TRAINER, Permission.ORGANIZATION_READ)
    assert not has_permission(Role.TRAINER, Permission.SALE_READ_ALL)

