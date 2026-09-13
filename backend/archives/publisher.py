PUBLISHER_GROUP_NAME = "Organic Archives Publishers"

PUBLISHER_PERMISSION_CODENAMES = frozenset(
    f"{action}_{model}"
    for model in ("post", "postblock")
    for action in ("add", "change", "delete", "view")
)
