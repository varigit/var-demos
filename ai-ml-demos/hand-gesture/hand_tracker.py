#
# Origin: https://github.com/wolterlw/hand_tracking
# Copyright 2020-2022 NXP
#
# SPDX-License-Identifier: Apache-2.0
# Modified by Variscite in 2026: bounded numerics, tensor validation,
# confidence gating, separate delegates and explicit error propagation.
#

import csv
from time import monotonic
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

class HandTracker():
    r"""
    Class to use Google's Mediapipe HandTracking pipeline from Python.
    So far only detection of a single hand is supported.
    Any any image size and aspect ratio supported.

    Args:
        palm_model: path to the palm_detection.tflite
        joint_model: path to the hand_landmark.tflite
        anchors_path: path to the csv containing SSD anchors
    Ourput:
        (21,2) array of hand joints.
    Examples::
        >>> det = HandTracker(path1, path2, path3)
        >>> input_img = np.random.randint(0,255, 256*256*3).reshape(256,256,3)
        >>> keypoints, bbox = det(input_img)
    """

    def __init__(self, palm_model, joint_model, anchors_path, delegate_path,
                box_enlarge=1.5, box_shift=0.2, progress=None):
        self.box_shift = box_shift
        self.box_enlarge = box_enlarge
        self.inference_seconds = 0.0
        self.progress = progress or (lambda _message: None)
        self.palm_prepared = False
        self.joint_prepared = False
        self.progress('Loading palm and landmark models')

        if(delegate_path):
            self.interp_palm = tflite.Interpreter(
                palm_model, num_threads=1,
                experimental_delegates=[tflite.load_delegate(delegate_path)])
            self.interp_joint = tflite.Interpreter(
                joint_model, num_threads=1,
                experimental_delegates=[tflite.load_delegate(delegate_path)])
        else:
            self.interp_palm = tflite.Interpreter(palm_model)
            self.interp_joint = tflite.Interpreter(joint_model)
        self.progress('Allocating model tensors and NPU delegates')
        self.interp_palm.allocate_tensors()
        self.interp_joint.allocate_tensors()
        for interpreter in (self.interp_palm, self.interp_joint):
            detail = interpreter.get_input_details()[0]
            if (tuple(detail['shape']) != (1, 256, 256, 3)
                    or detail['dtype'] != np.float32):
                raise ValueError('Expected float32 256x256 model input')
        
        # reading the SSD anchors
        with open(anchors_path, "r") as csv_f:
            self.anchors = np.r_[
                [x for x in csv.reader(csv_f, quoting=csv.QUOTE_NONNUMERIC)]
            ]
        # reading tflite model paramteres
        output_details = self.interp_palm.get_output_details()
        input_details = self.interp_palm.get_input_details()
        
        self.in_idx = input_details[0]['index']
        self.out_reg_idx = output_details[1]['index']
        self.out_clf_idx = output_details[0]['index']
        
        self.in_idx_joint = self.interp_joint.get_input_details()[0]['index']
        self.out_idx_joint = self.interp_joint.get_output_details()[0]['index']
        joint_outputs = self.interp_joint.get_output_details()
        self.presence_index = next(
            (detail['index'] for detail in joint_outputs
             if 'handflag' in detail['name'].lower()), None)

        # 90° rotation matrix used to create the alignment trianlge        
        self.R90 = np.r_[[[0,1],[-1,0]]]

        # trianlge target coordinates used to move the detected hand
        # into the right position
        self._target_triangle = np.float32([
                        [128, 128],
                        [128,   0],
                        [  0, 128]
                    ])
        self._target_box = np.float32([
                        [  0,   0, 1],
                        [256,   0, 1],
                        [256, 256, 1],
                        [  0, 256, 1],
                    ])
    
    def _get_triangle(self, kp0, kp2, dist=1):
        """get a triangle used to calculate Affine transformation matrix"""

        dir_v = kp2 - kp0
        norm = np.linalg.norm(dir_v)
        if not np.isfinite(norm) or norm < 1e-6:
            raise ValueError('Degenerate palm alignment')
        dir_v /= norm

        dir_v_r = dir_v @ self.R90.T
        return np.float32([kp2, kp2+dir_v*dist, kp2 + dir_v_r*dist])

    @staticmethod
    def _triangle_to_bbox(source):
        # plain old vector arithmetics
        bbox = np.c_[
            [source[2] - source[0] + source[1]],
            [source[1] + source[0] - source[2]],
            [3 * source[0] - source[1] - source[2]],
            [source[2] - source[1] + source[0]],
        ].reshape(-1,2)
        return bbox
    
    @staticmethod
    def _im_normalize(img):
        # Model distributor specifies (RGB - 128) / 128, not RGB / 127.5.
        return np.ascontiguousarray((img.astype(np.float32) - 128) / 128)
       
    @staticmethod
    def _sigm(x):
        return 1 / (1 + np.exp(-np.clip(x, -80, 80)))
    
    @staticmethod
    def _pad1(x):
        return np.pad(x, ((0,0),(0,1)), constant_values=1, mode='constant')
    
    def predict_joints(self, img_norm):
        self.interp_joint.set_tensor(
            self.in_idx_joint, img_norm.reshape(1,256,256,3))
        started = monotonic()
        if not self.joint_prepared:
            self.progress('Preparing landmark model on the NPU (first inference)')
        self.interp_joint.invoke()
        self.joint_prepared = True
        self.inference_seconds += monotonic() - started
        if self.presence_index is not None:
            confidence = float(self.interp_joint.get_tensor(
                self.presence_index).reshape(-1)[0])
            # This legacy model's handflag is not a calibrated probability.
            # Presence comes from the palm detector's 0.95 score threshold.
            if not np.isfinite(confidence):
                return None

        joints = self.interp_joint.get_tensor(self.out_idx_joint)[0]
        if joints.shape != (63,) or not np.isfinite(joints).all():
            raise RuntimeError('Invalid hand landmark output')
        joints = joints.tolist()
        del joints[2::3]
        joints = np.array(joints)
        a = joints.reshape(-1,2)
        return a

    def detect_hand(self, img_norm):
        assert -1 <= img_norm.min() and img_norm.max() <= 1,\
        "img_norm should be in range [-1, 1]"
        assert img_norm.shape == (256, 256, 3),\
        "img_norm shape must be (256, 256, 3)"

        # predict hand location and 7 initial landmarks
        self.interp_palm.set_tensor(self.in_idx, img_norm[None])
        started = monotonic()
        if not self.palm_prepared:
            self.progress('Preparing palm model on the NPU (first inference)')
        self.interp_palm.invoke()
        self.palm_prepared = True
        self.inference_seconds += monotonic() - started

        out_reg = self.interp_palm.get_tensor(self.out_reg_idx)[0]
        out_clf = self.interp_palm.get_tensor(self.out_clf_idx)[0,:,0]

        # finding the best prediction
        detecion_mask = self._sigm(out_clf) > 0.95
        candidate_detect = out_reg[detecion_mask]
        candidate_anchors = self.anchors[detecion_mask]

        if candidate_detect.shape[0] == 0:
            return None, None
        # picking the widest suggestion while NMS is not implemented
        max_idx = np.argmax(candidate_detect[:, 3])

        # bounding box offsets, width and height
        dx,dy,w,h = candidate_detect[max_idx, :4]
        center_wo_offst = candidate_anchors[max_idx,:2] * 256
        
        # 7 initial keypoints
        keypoints = center_wo_offst + candidate_detect[max_idx,4:].reshape(-1,2)
        side = max(w,h) * self.box_enlarge
        
        # now we need to move and rotate the detected hand for it to occupy a
        # 256x256 square
        # line from wrist keypoint to middle finger keypoint
        # should point straight up
        source = self._get_triangle(keypoints[0], keypoints[2], side)
        source -= (keypoints[0] - keypoints[2]) * self.box_shift
        return source, keypoints

    def preprocess_img(self, img):
        # fit the image into a 256x256 square
        rows, columns = img.shape[:2]
        side = max(rows, columns)
        pad = np.array([(side - rows) // 2, (side - columns) // 2])
        img_pad = np.pad(
            img,
            ((pad[0], side - rows - pad[0]),
             (pad[1], side - columns - pad[1]), (0, 0)),
            mode='constant')
        img_small = cv2.resize(img_pad, (256, 256))
        img_small = np.ascontiguousarray(img_small)
        
        img_norm = self._im_normalize(img_small)
        return img_pad, img_norm, pad

    def __call__(self, img):
        self.inference_seconds = 0.0
        img_pad, img_norm, pad = self.preprocess_img(img)
        
        try:
            source, keypoints = self.detect_hand(img_norm)
            if source is None:
                return None, None

            # calculating transformation from img_pad coords
            # to img_landmark coords (cropped hand image)
            scale = img_pad.shape[0] / 256
            Mtr = cv2.getAffineTransform(
                source * scale,
                self._target_triangle)
    
            img_landmark = self._im_normalize(cv2.warpAffine(
                img_pad, Mtr, (256, 256)))
        
            joints = self.predict_joints(img_landmark)
            if joints is None:
                return None, None
        
            # adding the [0,0,1] row to make the matrix square
            Mtr = self._pad1(Mtr.T).T
            Mtr[2,:2] = 0
            Minv = np.linalg.inv(Mtr)

            # projecting keypoints back into original image coordinate space
            kp_orig = (self._pad1(joints) @ Minv.T)[:,:2]
            box_orig = (self._target_box @ Minv.T)[:,:2]
            kp_orig -= pad[::-1]
            box_orig -= pad[::-1]
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            kp_orig, box_orig = None, None
        
        return kp_orig, box_orig
