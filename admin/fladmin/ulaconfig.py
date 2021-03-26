feature = {
    "1": "Get Bot",
    "2": "Post Stats"
}

method = {
    "1": "GET",
    "2": "POST",
    "3": "PATCH",
    "4": "PUT",
    "5": "DELETE"
}

method_choices = [(int(choice_num), choice_text) for choice_num, choice_text in method.items()]
feature_choices = [(int(choice_num), choice_text) for choice_num, choice_text in feature.items()]

positive_choices = (
    (0, 'Negative'),
    (1, 'Positive'),
    (2, 'Neutral')
)
