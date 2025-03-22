import os
import re
import subprocess
import json

import OpenEXR
import PySide2
import sys 
from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea, QGroupBox, QFormLayout, QLabel, QCheckBox, QStyle, QMessageBox
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QIcon

core = PySide2.QtCore
widgets = PySide2.QtWidgets
gui = PySide2.QtGui


def isAovInVariance(aov_names: list[str]):
    variance_dict = {
    "alpha" : "mse", 
    "diffuse": "diffuse_mse", 
    "specular": "specular_mse", 
    "albedo" : "albedo_mse",
    "normal" : "normal_mse",
    "position" : "mse",
    "lpe" : "mse",
    "other" : "mse"
    }
    variance_layers = []
    
    for aov in aov_names:
        for key in variance_dict.keys():
            if key in aov:  # Check if a variance key is in the AOV name
                variance_layers.append(variance_dict[key])  # Get the corresponding value (variance layer)
                
            elif aov.lower() == "a" or "alpha":
                variance_layers.append(variance_dict["alpha"])    
            elif aov.lower() == "N" :
                variance_layers.append(variance_dict["normal"])
            elif aov.lower() == "P" :
                variance_layers.append(variance_dict["position"])
            elif "lpe" in aov.lower() :
                variance_layers.append(variance_dict["lpe"])
            else :
                variance_layers.append(variance_dict["other"])
    
    return variance_layers

def addJsonAOV(FramesPath : str, aov_names : list[str], OutputFolder : str):
    JsonAovsToAdd = []
    variance_layers =  isAovInVariance(aov_names)
    OutputPathFile = os.path.join(OutputFolder, os.path.split(FramesPath)[1])
    for index, aov_name in enumerate(aov_names) :      
        add_aov = {
            "name": aov_name,

            "input": { "filename": FramesPath, "layer": aov_name },
            "input_variance": { "filename": FramesPath, "layer": variance_layers[index] },
    
            "outputs": [
                
                { "read": { "filename": FramesPath, "layer": aov_name }, "write": { "filename": OutputPathFile, "layer": aov_name } }
            ]
        }
        add_beauty = {
            "name": aov_name,

            "input": { "filename": FramesPath, "layer": aov_name },
            "input_variance": { "filename": FramesPath, "layer": variance_layers[index] },
    
            "outputs": [
                { "read": { "filename": FramesPath, "layer": aov_name }, "write": { "filename": OutputPathFile, "layer": "RGB" } }
            ]
        }

        add_alpha = {
            "name": aov_name,

            "input": { "filename": FramesPath, "layer": aov_name },
            "input_variance": { "filename": FramesPath, "layer": variance_layers[index] },
    
            "outputs": [
                { "read": { "filename": FramesPath, "layer": aov_name }, "write": { "filename": OutputPathFile, "layer": aov_name , "filters": [{ "type": "cutoff", "minValue": 0.0, "minCutoff": 0.00001, "maxValue": 1.0, "maxCutoff": 0.999}] }}
            ]
        }
        if aov_name.lower() == "beauty" :
            JsonAovsToAdd.append(add_beauty)
        elif aov_name.lower() == "a" or "alpha":
            JsonAovsToAdd.append(add_alpha) 
        else :
            JsonAovsToAdd.append(add_aov)
    
    return JsonAovsToAdd

# Create custom Json
def createJson(FramesPath : str, AOV_Names : list[str], InputFolder : str, FrameRange : str):
    # Create the folder if don't exists
    OutputFolder = InputFolder + "/FILTERED"
    if not os.path.exists(OutputFolder):
        os.makedirs(OutputFolder)
    rdm_denoise_config =    {
        "settings": {
            "progress": True,
            "albedo": {
                "filename": FramesPath,
                "layer": "albedo"
            },
            "albedo_variance": {
                "filename": FramesPath,
                "layer": "albedo_mse"
            },
            "normal": {
                "filename": FramesPath,
                "layer": "normal"
            },
            "normal_variance": {
                "filename": FramesPath,
                "layer": "normal_mse"
            },
            "sample_count": {
                "filename": FramesPath,
                "layer": "sampleCount"
            },
            "flow": {
                "filename": FramesPath,
                "layer": "Ci"
            },
            "frame-include": FrameRange,
            "parameters": "${RMANTREE}/lib/denoise/20970-renderman.param",
            "topology": "${RMANTREE}/lib/denoise/full_w7_4sv2_sym_gen2.topo",
            "asymmetry": 0.0,
            "tiles": [
                1,
                1
            ]
        },
        "passes": addJsonAOV(FramesPath, AOV_Names, OutputFolder)
    }
   
    global new_rdm_denoise_config_json_path
    new_rdm_denoise_config_json_path = os.path.join(OutputFolder ,r"rdm_denoise_config.json")
    with open(new_rdm_denoise_config_json_path, "w", encoding="utf-8") as f:
        json.dump(rdm_denoise_config, f, indent=4)

    print(f"JSON file '{new_rdm_denoise_config_json_path}' successfully generated.")
    return new_rdm_denoise_config_json_path


# Start denoise as subprocess
def RdmDenoiseStart(RendermanDenoisePath, JsonPath ):
    print("Launching Renderman denoising process...")
    batch_render =subprocess.call(
            [RendermanDenoisePath, '--json', JsonPath, "/s"],
            shell=True
        )



def isEndingWithFourDigitsAndEXR(File) :
    return re.search(r"([0-9][0-9][0-9][0-9]\.exr)", File)

def getFrameName(FramesDirectory, GetFirstFrame = False):

    frame_name =  next((frame_name for frame_name in os.listdir(FramesDirectory) if isEndingWithFourDigitsAndEXR(frame_name)), None)
    frame_names = re.sub(r"([0-9][0-9][0-9][0-9])(\.exr)", r"####\2", frame_name)
    
    global frame_path
    frame_path = os.path.join(FramesDirectory, frame_names)
    print(frame_path)
    if GetFirstFrame == True:
        frame_path = os.path.join(FramesDirectory, frame_name)
        return frame_path
    else :
        return frame_path
 




# Function to list all AOV contain in the EXR
def listExrAovs(file_path):
    # Open the EXR file
    exr_file = OpenEXR.InputFile(file_path)
    print(str(exr_file))
    # Check if an Aov as been already seen
    seen = set()
    # Get all channel names (AOVs)
    channels = exr_file.header()['channels'].keys()
    aovs = []
    for aov in channels : 
        aov = os.path.splitext(aov)[0]
        if aov not in seen:
            seen.add(aov)
            aovs.append(aov)
    print("Detected AOVs : " + str(aovs))
    return aovs


# Add all given AOV to the interface
def addAOVtoUI(AovsNames):  
    formLay = QFormLayout()
    aov_list = []
    checkbox_list = []
   
    for i,aov_name in enumerate(AovsNames):
        aov_object = QLabel(aov_name)
        checkbox_object = QCheckBox("")
        aov_list.append(aov_object)
        checkbox_list.append(checkbox_object)
        formLay.addRow(checkbox_list[i], aov_list[i])
    return formLay, aov_list, checkbox_list


# Start the denoise process
def startProcess(FramesDirectory, FrameRange):
    
    rdm_denoise_path = r"C:/Program Files/Pixar/RenderManProServer-26.3/bin/denoise_batch.exe"
    print(FrameRange)
    # Get frame_paths as frame_name.####.exr
    frame_path = getFrameName(FramesDirectory, False)

    # get all selected AOVs
    selected_aovs = []
    for index, aov in enumerate(RdmDenoiseUI.aov_list):
        if RdmDenoiseUI.checkbox_list[index].isChecked():
            selected_aovs.append(aov.text())
    print("Selected AOVs : " + str(selected_aovs))
    
    # Create the custom JSON
    createJson(frame_path,selected_aovs, FramesDirectory, FrameRange)
    
    # Launch Denoising
    RdmDenoiseStart(rdm_denoise_path,new_rdm_denoise_config_json_path)
    print("Denoising process finished")


# UI
class RdmDenoiseUI(QWidget): 
    checkbox_list = []
    aov_list = []

    button_style = "border-radius : 4; border : 0.5px solid #bbbbbb; padding : 4px"
    QLine_style = "border-radius : 4; border : 0.5px solid #bbbbbb; padding : 4px "
    window_style = "color: #212529;"
    Inputs_Height = 25

    def __init__(self): 
        super().__init__() 
        self.setGeometry(100, 100, 300, 200) 
       
        # Layout
        globalLayout = QVBoxLayout() 

        ## Input Layout
        InputLayout = QVBoxLayout() 
        Input_sublay = QHBoxLayout() 

        RefreshBtn_layout = QHBoxLayout()
        ## Aov Layout
        aov_layout = QVBoxLayout() 
        
        ## Denoise Layout
        Denoise_Layout = QHBoxLayout() 
        

        self.in_dir_label = widgets.QLabel("Frames Directory")
        self.in_dir_line = widgets.QLineEdit()
        self.in_dir_line.setPlaceholderText("Frames path") 
        self.in_dir_line.setStyleSheet(self.QLine_style)
        self.in_dir_line.setFixedHeight(self.Inputs_Height)
        self.in_dir_btn = QPushButton('Browse')
        self.in_dir_btn.setFixedHeight(self.Inputs_Height)
        self.in_dir_btn.setStyleSheet(self.button_style)
        
        self.refresh_aov_btn = QPushButton('')
        self.refresh_aov_btn.setStyleSheet(self.button_style)
        
        self.refresh_aov_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.frame_range_label = widgets.QLabel("Frame Range :")
        self.frame_range_min = widgets.QLineEdit()
        self.frame_range_min.setPlaceholderText("Min") 
        self.frame_range_min.setFixedWidth(40)
        self.minus_sign =  widgets.QLabel(" - ")
        self.frame_range_max = widgets.QLineEdit()
        self.frame_range_max.setFixedWidth(40)
        self.frame_range_max.setPlaceholderText("Max") 

        self.frame_range_min.setStyleSheet(self.QLine_style)
        self.frame_range_max.setStyleSheet(self.QLine_style)
        self.frame_range_min.setFixedHeight(self.Inputs_Height)
        self.frame_range_max.setFixedHeight(self.Inputs_Height)


        self.in_dir_line.editingFinished.connect(lambda : self.updateAOVs(self.in_dir_line.text()))

        self.groupBox = QGroupBox("AOVs")
        self.formLay, self.aov_list, self.checkbox_list = addAOVtoUI([]) # Empty AOV field
       
        self.groupBox.setLayout(self.formLay)
        groupBox = QGroupBox("AOVs")
        
        groupBox.setLayout(self.formLay)
        
        self.scrollarea = QScrollArea()
        self.scrollarea.setWidget(self.groupBox)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setMinimumHeight(500)
        self.scrollarea.setMinimumWidth(400)
        aov_layout.addWidget(self.scrollarea)


        self.denoise_btn = QPushButton('Denoise')
        self.denoise_btn.setStyleSheet(self.button_style)

        InputLayout.addWidget(self.in_dir_label)
        Input_sublay.addWidget(self.in_dir_line)
        Input_sublay.addWidget(self.in_dir_btn) 
        InputLayout.addLayout(Input_sublay)

        
        RefreshBtn_layout.addWidget(self.frame_range_label)
        RefreshBtn_layout.addWidget(self.frame_range_min) 
        RefreshBtn_layout.addWidget(self.minus_sign) 
        RefreshBtn_layout.addWidget(self.frame_range_max) 
        # RefreshBtn_layout.addWidget(self.husk_aov_checkbox)
        RefreshBtn_layout.addStretch()
        RefreshBtn_layout.addWidget(self.refresh_aov_btn)
        Denoise_Layout.addWidget(self.denoise_btn)
        

        globalLayout.addLayout(InputLayout)
        globalLayout.addLayout(RefreshBtn_layout)
        globalLayout.addLayout(aov_layout)
        globalLayout.addLayout(Denoise_Layout)

        self.in_dir_btn.clicked.connect(lambda: self.browseForFolder(self.in_dir_line)) 
        self.denoise_btn.clicked.connect(lambda: self.isFrameRangeComplete() ) 
        self.refresh_aov_btn.clicked.connect(lambda: self.updateAOVs(self.in_dir_line.text()))


        icon = QApplication.style().standardIcon(QStyle.SP_DirIcon)
        self.setWindowIcon(icon)
        self.setStyleSheet(self.window_style)
        self.setWindowTitle("RDM Denoise Launcher")

        
        self.setLayout(globalLayout)

    def ErrorWindow(Message : str):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(Message)
        msg.setWindowTitle("Error")
        msg.exec_()
        
    def isFrameRangeComplete(self) :
        if self.in_dir_line.text().replace(" ", "") == "" :
            RdmDenoiseUI.ErrorWindow("Frames directory cannot be empty")
            return
        if self.frame_range_min.text().replace(" ", "") == "" :
            RdmDenoiseUI.ErrorWindow("Frame range cannot be empty")
            return
        elif self.frame_range_max.text().replace(" ", "") == "" :
            RdmDenoiseUI.ErrorWindow("Frame range cannot be empty")
            return
        else :
            startProcess(self.in_dir_line.text(), self.frame_range_min.text() + "-" + self.frame_range_max.text())

             
    def updateAOVs(self, folder_path):

        first_frame_path = getFrameName(folder_path,True)
        # if self.husk_aov_checkbox.isChecked():
        #     aovs_names = listExrAovsHuskStat(first_frame_path) 
        # else :
        aovs_names = listExrAovs(first_frame_path) 
        RdmDenoiseUI.aov_list.clear()
        RdmDenoiseUI.checkbox_list.clear()
        

        if self.scrollarea.widget():
            self.scrollarea.widget().setParent(None) 

        self.groupBox = QGroupBox("AOVs")  
        formLay, RdmDenoiseUI.aov_list, RdmDenoiseUI.checkbox_list = addAOVtoUI(aovs_names)
        self.groupBox.setLayout(formLay)

        self.scrollarea.setWidget(self.groupBox)

        self.scrollarea.repaint()

        self.scrollarea.update()
        self.repaint()
        


    def browseForFolder(self, Input):
        #Get Folder
        dirname = str(widgets.QFileDialog.getExistingDirectory(None,"Select Directory for Export"))
        if dirname:
            Input.setText(dirname)
            self.updateAOVs(dirname)

    
if __name__ == "__main__": 
    app = QApplication(sys.argv) 
    window = RdmDenoiseUI() 
    window.show() 
    sys.exit(app.exec_())

    