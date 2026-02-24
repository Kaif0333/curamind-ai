def is_patient(user):
    return user.is_authenticated and user.user_type == "patient"


def is_doctor(user):
    return user.is_authenticated and user.user_type == "doctor"


def is_admin(user):
    return user.is_authenticated and user.is_staff
