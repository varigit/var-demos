# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

from pyvar.ml.engines.armnn import ArmNNInterpreter
from pyvar.ml.utils.label import Label
from pyvar.ml.utils.overlay import Overlay
from pyvar.ml.utils.resizer import Resizer
from pyvar.ml.utils.retriever import FTP
from pyvar.multimedia.helper import Multimedia

ftp = FTP()

if ftp.retrieve_package(category="detection"):
    model_file_path = ftp.model
    label_file_path = ftp.label
    image_file_path = ftp.image

labels = Label(label_file_path)
labels.read_labels("detection")

engine = ArmNNInterpreter(model_file_path, accelerated=True)

resizer = Resizer()

image = Multimedia(image_file_path)
resizer.resize_image(image.video_src, engine.input_width, engine.input_height)

engine.set_input(resizer.image_resized)

engine.run_inference()

engine.get_result("detection")

draw = Overlay()

output_image = draw.info(category="detection",
                         image=resizer.image,
                         top_result=engine.result,
                         labels=labels.list,
                         inference_time=engine.inference_time,
                         model_name=model_file_path,
                         source_file=resizer.image_path)

image.show_image("ArmNN: Image Detection", output_image)
