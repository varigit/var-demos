# Running Machine Learning Examples on the i.MX 93

The i.MX 93 is slightly different from the i.MX8M Plus when we need to run
Machine Learning examples on the NPU. For more information, please read the
following document from NXP:

* [i.MX Machine Learning User's Guide](https://www.nxp.com/docs/en/user-guide/IMX-MACHINE-LEARNING-UG.pdf)

Basically, we should not use the `libvxdelegate` library anymore, this is only
for the 8 family. We need to use the `ethosu` library to load the model to the
microNPU for the i.MX 93. Check the difference:

* i.MX8M Plus:

   ```python
   from tflite_runtime.interpreter import Interpreter
   interpreter = Interpreter(model_path="path/to/the/model")
   ```

* i.MX 93:

   ```python
   import ethosu.interpreter as ethosu
   interpreter = ethosu.Interpreter("path/to/the/model")
   ```
   
Firstly, we need to take the model and convert it to use on the Ethos u65 microNPU.
We load the converted model (vela) using the TensorFlow Lite API (ethosu library),
then the engine calls the Ethos-U Linux driver and dispatches the customized Ethos-U
operator to the Ethos-U firmware on Cortex-M reaching the Ethos-U NPU.

## Installing the Ethos-u-Vela Tool

   ```sh
   $ git clone https://github.com/nxp-imx/ethos-u-vela.git cd && ethos-u-vela
   $ git checkout lf-5.15.71_2.2.0
   $ pip3 install . 
   ```

## Converting the model using Ethos-u-Vela

   ```sh
   $ vela model_example.tflite
   ```

Then, you will get the `model_example_vela.tflite` model.
