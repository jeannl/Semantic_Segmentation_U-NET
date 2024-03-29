import dataset
import config
import numpy as np
import torch
import os
import utils
import torchvision
import platform

class TestModel:
	def __init__(self, model, transforms, metrics):
		self.model = model
		self.transforms = transforms
		self.metrics = metrics

	@staticmethod
	def classToColorForPred(pred):
		# We pick up the list of labeled classes in the csv file.
		labeledClasses = dataset.SegmentationDataset.openColorizedClassesCSV()

		colors = list(labeledClasses.values())
		colors = np.array(colors)

		# We use a threshold in the case of a binary classification.
		if config.NBR_CLASSES == 1:
			# We define the type of threshold for a binary classification
			if config.THRESHOLD_TYPE == "mean":
				value = np.mean(pred, axis=None)
			if config.THRESHOLD_TYPE == "median":
				value = np.median(pred, axis=None)

			# We create a mask in function of the threshold
			mask = pred >= value
			# We create a new dimension
			mask = mask[..., np.newaxis]
			# We convert a mask in colored image
			mask = np.where(mask, colors[0], colors[1]).astype(int)
			# Tris transpose is import in order to be consistent about .T for plotting
			return mask.transpose(2, 0, 1)

		else:
			# We take the most probable class for each pixel
			mask = [
						[
							np.argmax(dim) for dim in row
						] for row in pred.T
					]

			return np.array(colors[mask]).T.astype(int)

	def createFilename(imagePath):
		# find the filename and generate the path to ground truth
		# mask
		filename = imagePath.split(os.path.sep)[-1]

		# Select just the filename without the extension
		filenameSplit = filename.split(".")
		imagePaths = sorted(list(utils.list_images(config.MASK_DATASET_PATH)))
		_, extension = os.path.splitext(os.path.join(imagePaths[0]))

		return filenameSplit[-2] + extension

	def openTorchImage(self, imagePath):
		# Load up the image using the path argument
		image = torchvision.io.read_image(imagePath, torchvision.io.ImageReadMode.RGB)
		image = self.transforms(image)

		# make the channel axis to be the leading one, add a batch
		# dimension, and flash it to the current device
		image = torch.unsqueeze(image, dim=0)

		return image.to(config.DEVICE)

	def openTorchGTImage(self, filename):
		# Load the ground-truth segmentation mask in grayscale mode
		# and resize it
		# TODO change that in the future
		if config.AUG_DATA :
			path = config.AUGMENTED_DATA_MASK_PATH
			splitFilename = filename.split("_")
			filename = ["mask"] + splitFilename[1:]
			filename = "_".join(filename)
		else:
			path = config.MASK_DATASET_PATH

		groundTruthPath = os.path.join(path, filename)

		if config.ACTIVATE_LABELED_CLASSES == False:
			gtMask = torchvision.io.read_image(groundTruthPath, torchvision.io.ImageReadMode.GRAY)

			gtMask = self.transforms(gtMask)

			# Compute mean and std for images
			mean, std = torch.mean(gtMask.float(), dim=(1, 2)), torch.std(gtMask.float(), dim=(1, 2))

			# Add Normalization transformation just for the mask
			normalization = torchvision.transforms.Compose([torchvision.transforms.Normalize(mean, std)])
			gtMask = normalization(gtMask)

			# We make the training mask dataset according the right number of class
			gtMask = dataset.SegmentationDataset.convertToAdaptedTensorMask(
				mask=gtMask,
				shape = [
					config.NBR_CLASSES,
					config.INPUT_IMAGE_HEIGHT,
					config.INPUT_IMAGE_WIDTH
				]
			)

			return gtMask, None

		else:
			gtMask = torchvision.io.read_image(groundTruthPath, torchvision.io.ImageReadMode.RGB)

			# We want to retun a result without a transformation in tensor
			transformForMaskRGB = torchvision.transforms.Compose(self.transforms.transforms[:-1])
			return  self.transforms(gtMask), transformForMaskRGB(gtMask)

	def plotPrediction(input, torchMask, pred, maskRGB, name, errorMap):
		plots =[]
		plotTitles = []

		# We create a list of dim mask that we want to plot
		plots.append(input[0].cpu().T)
		plotTitles.append("Original Image")
		plots.append(maskRGB[0].T)
		plotTitles.append("Original Mask RGB")

		# We plot just one dimension for nbr_classes egual to 1
		if (config.NBR_CLASSES == 1 and config.ACTIVATE_LABELED_CLASSES == False) or config.NBR_CLASSES == 2:
			plots.append(torchMask[0].cpu().T)
			plotTitles.append("Binary mask")
			#plots.append(pred[0].cpu().detach().numpy().T)
			plots.append(errorMap.T)
			plotTitles.append("Error Map")

		else:

			plots.append(torchMask[0].cpu().T)
			plotTitles.append("Segmented Mask Prediction")

			for i in range(config.VISUALIZATION_DIM):
				plots.append(pred[0, i].cpu().detach().numpy().T)
				plotTitles.append(f"Probabilistic Prediction for dim {i}/{config.NBR_CLASSES - 1}")

		# Build and check my folder for plots
		utils.folderExists(config.PLOT_TEST_PATH)

		utils.prepare_plot(
			plots,
			plotTitles,
			os.path.join(config.PLOT_TEST_PATH, name),
			"Plot training model samples for the first image of each batch",
			mode="test"
		)

	def make_predictions(self, imagePath, index):
		# set model to evaluation mode
		self.model.eval()

		# turn off gradient tracking
		with torch.no_grad():

			# Open the original image
			image = TestModel.openTorchImage(self, imagePath)

			# Save an original image
			orig = image.clone()

			# Find the filename for the image
			filename = TestModel.createFilename(imagePath)

			# Define a name
			name = "Prediction_img_" + filename.split(".")[0] + "_index_" + str(index)

			# Open the ground-truth related with the image
			gtMask, gtMask255range = TestModel.openTorchGTImage(self, filename)

			# Make the prediction, pass the results through the sigmoid
			# function, and convert the result to a NumPy array
			prediction = self.model(image).squeeze()
			prediction = torch.sigmoid(prediction)
			prediction = prediction.cpu().numpy()

			# We change the prediction matrix in colored image instead of class matrix
			colorPred = TestModel.classToColorForPred(prediction)

			utils.folderExists(config.PLOT_METRICS)

			if config.NBR_CLASSES == 1 and config.ACTIVATE_LABELED_CLASSES == False:
				# Compute binary mask
				gtUnlabeledClass = dataset.SegmentationDataset.convertToAdaptedTensorMask(
					gtMask,
					shape = [
						config.NBR_CLASSES,
						config.INPUT_IMAGE_HEIGHT,
						config.INPUT_IMAGE_WIDTH
					]
					)

				# Indices
				gt_indices = gtUnlabeledClass.squeeze() == 1
				gt_indices = gt_indices.int()
				pred_indices = prediction > np.mean(prediction)
				pred_indices = torch.from_numpy(pred_indices).int()

				# Plot confusion matrix
				self.metrics.confusionMatrix(name, pred_indices.flatten(), gt_indices.flatten())

				# Compute error map
				errorMap =  pred_indices - gt_indices

				# Save other metrics
				self.metrics.addValueToMetrics(pred_indices, gt_indices, prediction, gt_indices, name)

			elif config.NBR_CLASSES == 2 and config.ACTIVATE_LABELED_CLASSES == True:
				# Add value to metrics class
				gtMaskTensor = dataset.SegmentationDataset.convertToLabeledTensorMask(
				gtMask255range,
				shape=[
					config.NBR_CLASSES,
					config.INPUT_IMAGE_HEIGHT,
					config.INPUT_IMAGE_WIDTH
				]
				)

				# We want a matrix who code index labels
				pred_indices = torch.argmax(torch.from_numpy(prediction), dim=0)
				gt_indices = torch.argmax(gtMaskTensor, dim=0)

				# Plot confusion matrix
				self.metrics.confusionMatrix(name, pred_indices, gt_indices)

				# Compute error map
				errorMap =  pred_indices - gt_indices

				# Save other metrics
				self.metrics.addValueToMetrics(pred_indices, gt_indices, np.max(prediction, axis=0), gt_indices, name)

			else:
				# Add value to metrics class
				gtMaskTensor = dataset.SegmentationDataset.convertToLabeledTensorMask(
				gtMask255range,
				shape=[
					config.NBR_CLASSES,
					config.INPUT_IMAGE_HEIGHT,
					config.INPUT_IMAGE_WIDTH
				]
				)

				# We want a matrix who code index labels
				pred_indices = torch.argmax(torch.from_numpy(prediction), dim=0)
				gt_indices = torch.argmax(gtMaskTensor, dim=0)

				# Plot confusion matrix
				self.metrics.confusionMatrix(name, pred_indices, gt_indices)

				# Define error map
				errorMap = None

				# Save other metrics TODO: it is wrong here
				self.metrics.addValueToMetrics(pred_indices, gt_indices, prediction, gtMaskTensor, name)

			# We plot our predictions
			TestModel.plotPrediction(
				orig,
				torch.tensor(colorPred).unsqueeze(dim=0),
				torch.tensor(prediction).unsqueeze(dim=0),
				gtMask.unsqueeze(dim=0),
				name,
				errorMap
			)

	def makePredictionDataset(self, imagePaths):
		# iterate over the randomly selected test image paths
		utils.logMsg("Start of predictions...", "test")

		# Delete old plots for metrics and test
		utils.deleteFolder(config.PLOT_METRICS)
		utils.deleteFolder(config.PLOT_TEST_PATH)

		for index, path in enumerate(imagePaths):
			# make predictions and visualize the results
			TestModel.make_predictions(self, path, index)
			utils.logMsg(f"Prediction {index+1} on {len(imagePaths)} done.", "test")

		# Plot mean metrics
		self.metrics.meanConfusionMatrix()

		# Write other metrics
		self.metrics.writeMeanMetrics()

		# We save all logs and errors in our specific id file
		# Useful just for Gricad
		if platform.system() == 'Linux':
			utils.saveLogs()
