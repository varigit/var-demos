# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Shared task/input navigation for curses and plain terminal menus."""

NPU_NAMES = {'imx8mplus': 'VIP8000', 'imx93': 'Ethos-U65', 'imx95': 'Neutron'}
TASKS = {'classification': ('Classification', 'Identify the main image category'),
         'detection': ('Object Detection', 'Find objects and draw bounding boxes'),
         'face': ('Face Detection', 'Find faces and draw bounding boxes'),
         'segmentation': ('People and Vehicle Segmentation', 'Paint people and vehicles; experimental'),
         'people-segmentation': ('People Segmentation', 'Lightweight person/background masks; experimental')}


def clean_title(title):
    for name in NPU_NAMES.values():
        title = title.replace(f' with {name}', '')
    return title


def demo_entries(launchers):
    """Group shared task modes, leaving platform-specific extras as entries."""
    entries, tasks = [], {}
    for launcher in launchers:
        name = launcher['id']
        for prefix in ('ethosu-', 'neutron-'):
            name = name.removeprefix(prefix)
        task, _, mode = name.rpartition('-')
        if task not in TASKS or mode not in ('image', 'video', 'camera'):
            # Extras remain self-describing at task level, even when their
            # old flat-menu label was only "Camera" or "Video".
            entries.append(dict(launcher, menu_title=(
                'Hand Gestures (Experimental)' if name == 'hand-gesture-camera'
                else clean_title(launcher.get('title', name)))))
            continue
        if task not in tasks:
            title, description = TASKS[task]
            tasks[task] = dict(id=task, title=title, description=description, children=[])
            entries.append(tasks[task])
        tasks[task]['children'].append(dict(launcher, menu_title=mode.title()))
    for task in tasks.values():
        task['children'].sort(key=lambda item: ('Image', 'Video', 'Camera').index(item['menu_title']))
    return entries
