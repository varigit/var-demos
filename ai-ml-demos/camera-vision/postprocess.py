# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import numpy as np


def decode_ssdlite(encodings, logits, priors, threshold=.5, iou=.45,
                   limit=20):
    """Decode SSD center/size anchors; background is class zero."""
    encodings = np.asarray(encodings).reshape(-1, 4)
    logits = np.asarray(logits).reshape(len(encodings), -1)
    priors = np.asarray(priors)
    if priors.shape != (4, len(encodings)):
        raise ValueError('SSD anchors do not match model output')
    if not np.isfinite(encodings).all() or not np.isfinite(logits).all():
        raise ValueError('Non-finite detector output')
    classes = np.argmax(logits[:, 1:], axis=1) + 1
    values = logits[np.arange(len(logits)), classes]
    scores = 1 / (1 + np.exp(-np.clip(values, -80, 80)))
    selected = np.flatnonzero(scores >= threshold)
    selected = selected[np.argsort(scores[selected])[::-1]][:200]
    raw = encodings[selected]
    anchor = priors[:, selected].T
    centers = raw[:, :2] / 10 * anchor[:, 2:] + anchor[:, :2]
    sizes = np.exp(np.clip(raw[:, 2:] / 5, -20, 20)) * anchor[:, 2:]
    boxes = np.clip(np.concatenate((centers - sizes / 2,
                                    centers + sizes / 2), axis=1), 0, 1)
    result = []
    order = list(range(len(selected)))
    while order and len(result) < limit:
        index = order.pop(0)
        y0, x0, y1, x1 = boxes[index]
        if y1 <= y0 or x1 <= x0:
            continue
        candidate = selected[index]
        result.append((boxes[index], int(classes[candidate]),
                       float(scores[candidate])))
        remaining = []
        for other in order:
            if classes[selected[other]] != classes[candidate]:
                remaining.append(other)
                continue
            low = np.maximum(boxes[index, :2], boxes[other, :2])
            high = np.minimum(boxes[index, 2:], boxes[other, 2:])
            intersection = np.prod(np.maximum(high - low, 0))
            area = np.prod(boxes[index, 2:] - boxes[index, :2])
            other_area = np.prod(boxes[other, 2:] - boxes[other, :2])
            overlap = intersection / max(area + other_area - intersection, 1e-9)
            if overlap <= iou:
                remaining.append(other)
        order = remaining
    return result


def decode_postprocessed(outputs, threshold=.5):
    """TFLite Detection_PostProcess emits boxes, classes, scores, count."""
    boxes, classes, scores, count = outputs
    count = min(int(np.asarray(count).flat[0]), len(np.asarray(scores).ravel()))
    if not all(np.isfinite(value).all() for value in outputs):
        raise ValueError('Non-finite detector output')
    return [(np.clip(box, 0, 1), int(class_id), float(score))
            for box, class_id, score in zip(
                boxes[0][:count], classes[0][:count], scores[0][:count])
            if score >= threshold and box[2] > box[0] and box[3] > box[1]]
