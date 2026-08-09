from fastapi.routing import APIRoute


def to_camel_case(value: str) -> str:
    head, *rest = value.split("_")
    return head + "".join(word.capitalize() for word in rest)


def operation_id_for(route: APIRoute) -> str:
    return to_camel_case(route.name)
