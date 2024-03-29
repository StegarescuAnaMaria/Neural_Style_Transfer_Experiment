# Neural-Style-Transfer-Experiment

   I developed an app that lets the user pick a content image and a style image at random and then attempt to simulate, by drawing, what a Neural Style Transfer (NST) Network would do: combine the content and style into one resulting image. I also present two different NST AIs and their outcome. As the last step, the user can view the results of the comparison between the 3 images (the drawing and the 2 stylized pictures), which will be a grade between 0 and 10.
   
   ![](pictures/image2.png)

   The [main NST model](https://colab.research.google.com/github/sayakpaul/Adventures-in-TensorFlow-Lite/blob/master/Style_Transfer_Demo_InceptionV3_Dynamic_Shape.ipynb) used by me for this project is a model licensed by Apache-2.0, which I researched on. This model uses an architecture for extracting the style from the style image, and another one for applying the style to the content image, plus the old-fashioned VGG architecture for calculating the style and content losses. 
   
   ![](pictures/image5.png)
	
   The [original Neural Style Transfer](https://github.com/AyushExel/Neural-Style-Transfer) architecture (VGG-19 in 2015) starts with the target image (copy of content image), extracting the gram matrixes which contain correlations between different filter responses of the style image (they contain the style, to put it briefly) and calculate the style loss in comparison to the style filter response of the target image. Same happens with the content correlations for the content loss, but the gram matrix is not computed in this case. The target image is optimized according to the loss until we get a stylized image as a result. 
	
  The main model does a better job, as it extracts the style in a bottleneck with the first architecture trained on style prediction. It relies solely on the theory that a lot of paintings have textures in common, so no matter the image, its style can be generalized as a mixture of styles the model learned while training. 
So the difference between the classic method and the new approach is that before calculating the loss, we make a style prediction and preprocess the content with it. The new method is an improved version of the VGG-19 NST and gives better and faster effects. In my app, I present the visible difference between the two methods and show both results.

   Another AI which I used is the model that compares the resulting images and gives the similarity. I built it by training an Autoencoder on reducing the content of an image and building the image back based only on the reduced result. In order to compare two images, I use just the encoder part and differentiate the reduced content. The user will be able to compare the 2 stylized images with each other, and the stylized images with their own drawing. This model uses the checkpoints from the folder "check1".
   
![](pictures/autoencoder.png)
	
   I made the graphical user interface with PyQt5. After the user picks a content image and a style image randomly, they can either upload their own image, or choose to draw a picture with the said content and style. Upon clicking the “Start to draw” button, a new window will appear with a drawing app. For this one, I designed my own brush textures to resemble the different kinds of paint used in the abstract art picked by me. 
   Here are 2 examples of the brush textures. Their color changes by user's liking.
   
   ![](pictures/image6.png)
   
   ![](pictures/image1.png)
	
   There is also a button for the image style transfer that starts the process. I left the button enabled from the start in case the user is curious about the result of the NST models. However, the process may take around 100-140 seconds (from my experiments), so while the user is busy drawing the picture, the style transfer process will start automatically on a 2nd thread. 
   
![](pictures/image3.png)

   The last step will be the comparison between the picture the user drew or uploaded, and the NST result following both approaches. 
   
  ![](pictures/image4.png)
  
I have created my own dataset of static images and abstract paintings, it can be downloaded [here](https://www.kaggle.com/anamariastegarescu/neural-style-transfer-dataset).

![](pictures/image7.png)

The icons used in the app are from https://icons8.com/.

The images used for the customized brush textures are from https://www.cleanpng.com/.

The abstract images are from https://theartling.com/en/art/abstract/.

The static images are from Google Images.
