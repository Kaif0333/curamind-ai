def is_patient(user):
    return user.is_authenticated and user.role == "PATIENT"


def is_doctor(user):
    return user.is_authenticated and user.role == "DOCTOR"


def is_admin(user):
    return user.is_authenticated and user.role == "ADMIN"
