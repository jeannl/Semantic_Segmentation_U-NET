import os
import config
import matplotlib.pyplot as plt
import utils
import shutil

def prepare_plot(plots, plotTitles, path, title="", mode="train"):
	# Initialize our figures
    if len(plots) <=4:
        figure, ax = plt.subplots(nrows= 1, ncols=4, figsize=(20, 10))
        figure.suptitle(title, fontsize=32)

        for index, value in enumerate(plots):
            ax[index].imshow(value)
            ax[index].set_title(plotTitles[index])

            if index == 3:
                im = ax[index].imshow(value, cmap=plt.cm.inferno)
                cbar = figure.colorbar(im, ax=ax[index])
                cbar.set_label("-1=FN 0=T 1=FP", size=16)

    else:
        figure, ax = plt.subplots(nrows= (len(plots) // 4) + 1, ncols=4, figsize=(20, 10))

        for index, value in enumerate(plots):
            ax[index // 4, index % 4].imshow(value)
            ax[index // 4, index % 4].set_title(plotTitles[index])

        # set the layout of the figure and display it
        figure.tight_layout()
        #figure.show()

    # Check if the file exists
    folderExists(config.PLOT_TRAIN_PATH)
    if mode == "test":
        folderExists(config.PLOT_TEST_PATH)

    figure.savefig(path)
    plt.close()

def folderExists(path):
	CHECK_FOLDER = os.path.isdir(path)

	# If folder doesn't exist, it creates it.
	if not CHECK_FOLDER:
		os.makedirs(path)
		logMsg("You created a new folder : " +  str(path), "data")

def deleteFolder(path):
    # Check if the folder exists
    if os.path.exists(path):
        # Remove the folder and its contents
        shutil.rmtree(path)
        logMsg("Folder deleted : " + str(path), "delete")
    else:
        logMsg("Folder does not exist : " + str(path), "delete")

def list_files(basePath, validExts=None, contains=None):
    # loop over the directory structure
    for (rootDir, dirNames, filenames) in os.walk(basePath):
        # loop over the filenames in the current directory
        for filename in filenames:
            # if the contains string is not none and the filename does not contain
            # the supplied string, then ignore the file
            if contains is not None and filename.find(contains) == -1:
                continue

            # determine the file extension of the current file
            ext = filename[filename.rfind("."):].lower()

            # check to see if the file is an image and should be processed
            if validExts is None or ext.endswith(validExts):
                # construct the path to the image and yield it
                imagePath = os.path.join(rootDir, filename)
                yield imagePath

def list_images(basePath, contains=None):
    # return the set of files that are valid
    return list_files(basePath, validExts=config.IMAGE_TYPES, contains=contains)

def logMsg(msg, type):
    if type == "info":
        print("[INFO] ", msg)
    elif type == "data":
        print("[DATA] ", msg)
    elif type == "error":
        print("[ERROR] ", msg)
    elif type == "time":
        print("[TIME] ", msg)
    elif type == "save":
        print("[SAVE] ", msg)
    elif type == "parallelism":
        print("[PARALLELISM] ", msg)
    elif type == "test":
        print("[TEST] ", msg)
    elif type == "delete":
        print("[DELETE] ", msg)
    else :
        print("[INFO] ", msg)

def saveConfig():
    with open(os.path.join(config.WORKING_DIRECTORY_PATH, "src", "config.py"), 'r') as py_file:
        content = py_file.read()

    utils.folderExists(os.path.join(config.BASE_OUTPUT, config.ID_SESSION))

    with open(os.path.join(config.BASE_OUTPUT, config.ID_SESSION, "SaveConfig_ID_" + str(config.ID_SESSION) + ".txt"), 'w') as txt_file:
        txt_file.write(content)

    logMsg("The config.py file has been saved in the id session folder.", "save")

def saveLogs():
    pathOutput = os.path.join(config.WORKING_DIRECTORY_PATH, "output.out")
    if os.path.isfile(pathOutput):
        with open(pathOutput, 'r') as py_file:
            content = py_file.read()
    else:
        pathOutput = ""
        content = ""

    pathError = os.path.join(config.WORKING_DIRECTORY_PATH, "error.err")
    if os.path.isfile(pathError):
        with open(pathError, 'r') as py_file:
            content = content + py_file.read()
    else:
        pathError = ""
        content = ""


    utils.folderExists(os.path.join(config.BASE_OUTPUT, config.ID_SESSION))

    with open(os.path.join(config.BASE_OUTPUT, config.ID_SESSION, "SaveOutputAndError" + str(config.ID_SESSION) + ".txt"), 'w') as txt_file:
        txt_file.write(content)

    logMsg("The Logs file has been saved in the id session folder.", "save")

def writeFile(meanMetrics, path):
    logMsg("We save metrics file.", "data")
    with open(path, 'w') as fichier:
        fichier.write("Mean Metrics :\n")
        for cle, moyenne in meanMetrics.items():
            fichier.write(f"{cle}: {moyenne}\n")
