from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')


@register.filter(name='match_slot')
def match_slot(assignments, args):
    """Return the first assignment matching semester and slot number."""
    sem, slot_number = args
    for item in assignments:
        if item.assignment.course.semester == sem and item.min_slot == slot_number:
            return item
    return None

@register.simple_tag
def get_matched_assignment(assignments, semester, slot_number):
    for item in assignments:
        if item['assignment'].course.semester == semester and item['min_slot'] == slot_number:
            return item
    return None

@register.filter
def times(number):
    """Repeat filter for a given number."""
    return range(int(number))

@register.simple_tag
def debug(obj):
    return str(obj)