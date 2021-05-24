// Modified 202102 by Robert Cudmore robert.cudmore@gmail.com
//
// 1) if image is RGB (like export on Olympus) then auto convert to 16-bit
// 2) expanded from 500 to 10,000 lcr
//	see abbMaxLCR = 10000
// 3) extracted l/t/r/b of each LCR ROI
//
//23532 // scan speed (lps) / 10
//829 // pixelsize (um) 0.829 = 829 / 1000
//25 // criterion = 2.5 = 25/10
//20
//1 // number of intervals
//1
//5
//2 // background fiu
//0
//1 //Extended Kinetics
//0

import ij.*;
import ij.plugin.filter.PlugInFilter;
import ij.process.*;
import ij.gui.*;
import java.awt.*;
//import java.awt.event.*;
import java.util.*;
//import java.lang.Math;
//import javax.swing.*;
//import ij.plugin.*;
import java.io.*;
import ij.measure.*;

//Oct22b laeuft mit korrekter Background Erkennung. Minimaler Unterschied bleibt, weiss aber nicht warum.
//Oct22c ist identisch mit Oct22b zeigt aber keine Zwischenwerte an.
//Dec11b	Time to Peak measurement included and max duration of sparks is now 2500 ms (only useful for long spark measurements)
//Dec12 a	Set max length of spark back to 250 ms
// Setzt alle Pixel auf 0, die kleiner sind als grenzwert * Standardabweichung


public class SparkMaster_20210220_ implements PlugInFilter {
	ImagePlus img;
	String title = "";		//define title here in order to make it available in the end
	int factorForOutput;
	int imageBit;		//0: 8-bit;		1: 16-bit

	//
	// abb adding these as member variables
	float tscan = (float)0.0029 * 1000; //"ms per line" tscan = (1/tscan)*1000; //Conversion from lps to 'ms per line'
	float psize = (float)0.829; // um/pixel
	boolean checkboxChoice[] = new boolean[]{false,true,false};	//this is the array for the default choices
	//checkboxChoice[0]=false;		//Ember Mode
	//checkboxChoice[1]=true;		//Extended Kinetics
	//checkboxChoice[2]=false;		//Analyze all open Images

	int choicechooseFilter = 1; // when 1 yields a 5x5 filter
	int choiceoutputImg = 0;
	int black = 2; //Background
	int nin = 1; //number of Intervals
	float cri = (float)2.5; //criterium 1
	float cri2 = 2; // not in interface

	String csvPath;

	public int setup(String arg, ImagePlus imp)
	 {
		if (arg.equals("about"))
			{showAbout(); return DONE;}


		int[] windowList = WindowManager.getIDList();
		if(windowList==null){
			IJ.noImage();// abb display imagej dialog
			return DONE;
		}

		////this.img = img;
		// abb get path and name of image
		IJ.log("activeImage:" + imp.getOriginalFileInfo()); // returns FileInfo
		String myFileName = imp.getOriginalFileInfo().fileName;
		String myDir = imp.getOriginalFileInfo().directory;
		IJ.log("myFileName:" + myFileName);
		IJ.log("myDir:" + myDir);
		csvPath = myDir + myFileName.replace(".tif", "_sm.csv");
		IJ.log("csvPath:" + csvPath);

		title = imp.getTitle();		//Title of the ImagePlus
		//IJ.showMessage("Title: "+title);
		imageBit = imp.getType();	//Type of ImagePlus: 0: 8-bit;  1: 16-bit
		IJ.log(" abb imageBit:" + imageBit);
		if (imageBit==4) {
			IJ.log("converting to 16 bit");
			new ImageConverter(imp).convertToGray16();
			imageBit = imp.getType();	//Type of ImagePlus: 0: 8-bit;  1: 16-bit
			IJ.log(" abb imageBit:" + imageBit);
		}
		return DOES_8G+DOES_8C+DOES_16+SUPPORTS_MASKING;
	} // setup

	public void abbShowDialog() {
		//These are the choices of the two drop-down lists in the GUI
		String[] outputImg = new String[6];		//These are the choices for which image is shown at the end
			outputImg[0] = "Raw";
			outputImg[1] = "Raw + Sparks";
			outputImg[2] = "Filtered";
			outputImg[3] = "Filtered + Sparks";
			outputImg[4] = "F/Fo";
			outputImg[5] = "F/Fo + Sparks";
		// abb removed
		//int choiceoutputImg;


		String[] chooseFilter = new String[4];		//Choices for initial Image filtering
			chooseFilter[0] = "Median 3 x 3";
			chooseFilter[1] = "Median 5 x 5";
			chooseFilter[2] = "Median 7 x 7";
			chooseFilter[3] = "Wavelet";
		// abb remove
		//int choicechooseFilter;


		//These are the three Checkboxes
		String checkboxLabel[]= new String[3];		//these are the Labels
			checkboxLabel[0]="Ember Mode";
			checkboxLabel[1]="Extended Kinetics";
			checkboxLabel[2]="Analyze all open Images";

		// abb removed
		//boolean checkboxChoice[] = new boolean[3];	//this is the array for the default choices

		int guiValue[] = new int[11];			//7 parameters are shown in the GUI
		float guiValueFl[] = new float[11];

		try					//This reads the GUI values from the harddrive
		{
			// read
			guiValue = lesen(guiValue);

			guiValueFl[0] = ((float)guiValue[0]/100);	//casts values read from the file to float
			guiValueFl[1] = ((float)guiValue[1]/1000);
			guiValueFl[2] = ((float)guiValue[2]/10);
			guiValueFl[3] = ((float)guiValue[3]/10);
			guiValueFl[4] = (float)guiValue[4];
			guiValueFl[5] = (float)guiValue[5];
			guiValueFl[6] = (float)guiValue[6];
			guiValueFl[7] = (float)guiValue[7];

			guiValueFl[8] = (float)guiValue[8];
			guiValueFl[9] = (float)guiValue[9];
			guiValueFl[10] = (float)guiValue[10];

		}
		catch (FileNotFoundException e)		//if file with values does not exist use default values
		{
		IJ.showMessage("SparkMasterV1.0.0 Mar02a      (c) 2006 by E. Picht           ");
			guiValueFl[0]=500;		//lps
			guiValueFl[1]=(float)0.149;	//Pixelsize
			guiValueFl[2]=(float)3.8;	//Criteria
			guiValueFl[3]=(float)2.0;	//Criteria 2 (not in the GUI anymore)
			guiValueFl[4]=1;		//No of Intervals
			guiValueFl[5]=1;		//Initial Filter
			guiValueFl[6]=5;		//Output Image
			guiValueFl[7]=10;		//Background

			guiValueFl[8]=0;		//Ember Mode
			guiValueFl[9]=1;		//Extended Kinetics
			guiValueFl[10]=0;		//Analyze all open Images

		}
		catch (IOException ioEx)			//any other IOException
		{
			IJ.showMessage("SparkMaster: IOException");
		}

		if(guiValueFl[8]==1) checkboxChoice[0]=true;	//convert from (float)guiValue to (boolean)checkboxChoice
		else checkboxChoice[0]=false;

		if(guiValueFl[9]==1) checkboxChoice[1]=true;	//convert from (float)guiValue to (boolean)checkboxChoice
		else checkboxChoice[1]=false;

		if(guiValueFl[10]==1) checkboxChoice[2]=true;	//convert from (float)guiValue to (boolean)checkboxChoice
		else checkboxChoice[2]=false;

		GenericDialog gd = new GenericDialog("SparkMaster       (c) 2006 by E. Picht");		//THIS IS THE GUI
			gd.addNumericField("Scanning Speed (lps):",guiValueFl[0],2);
			gd.addNumericField("Pixelsize (\u00B5m):",guiValueFl[1],3);
			gd.addNumericField("Background (Fl. U.):",guiValueFl[7],0);
			gd.addNumericField("Criteria:",guiValueFl[2],1);
		//	gd.addNumericField("Criteria 2:",guiValueFl[3],1);
			gd.addNumericField("No of Intervals:",guiValueFl[4],0);
		//	gd.addChoice("Initial Filter:", chooseFilter, chooseFilter[(int)guiValueFl[5]]);	//this has to be int
			gd.addChoice("Output Image:", outputImg, outputImg[(int)guiValueFl[6]]);		//this has to be int
			gd.addCheckboxGroup(3,1,checkboxLabel,checkboxChoice);


		gd.showDialog();

		if(gd.wasCanceled()){			//if canceled terminate here
			return;
		}

		//Read values from GUI
		//float tscan = (float)(1/gd.getNextNumber())*1000;		//lps
		// abb was this
		//float tscan = (float)gd.getNextNumber();			//reads lps
		tscan = (float)gd.getNextNumber();			//reads lps
			if(tscan<10){
				IJ.showMessage("Error","The Scanning Speed is too low.   ");
				return;
			}
		tscan = (1/tscan)*1000;				//Conversion from lps to ms
		//IJ.showMessage("tscan: "+tscan+"  ms");

		// abb was this
		//float psize = (float)gd.getNextNumber();			//pixelsize
		psize = (float)gd.getNextNumber();			//pixelsize
			if(psize<0.001){
				IJ.showMessage("Error","The Pixel size is too low.   ");
				return;
			}

		// abb was this
		//int black = (int)gd.getNextNumber();			//Background
		black = (int)gd.getNextNumber();			//Background
			if(black<0){
				IJ.error("Error","The Background is too low.   ");
				return;
			}
	//		if(black>510){
	//			IJ.error("Error","The Background is too high.   ");
	//			return;
	//		}

		// abb was this
		//float cri = (float)gd.getNextNumber();			//criterium 1
		cri = (float)gd.getNextNumber();			//criterium 1
			if(cri<2){
				IJ.error("Error","The Criteria is too low.   ");
				return;
			}

		//float cri2 = (float)gd.getNextNumber();			//criterium 2. This was previously in the Gui but removed at a later stage of development.
		// abb was this
		//float cri2 = 2;
		cri2 = 2;

		// abb was this
		//int nin = (int)gd.getNextNumber();			//number of Intervals
		nin = (int)gd.getNextNumber();			//number of Intervals
			if(nin<1) nin = 1;
			if(nin>5) nin = 5;

	//	choicechooseFilter = gd.getNextChoiceIndex();		//filter to apply. This was previously in the Gui but removed at a later stage of development.
		choicechooseFilter = 1;

		choiceoutputImg = gd.getNextChoiceIndex();		//outputImg

		checkboxChoice[0] = gd.getNextBoolean();		//Ember Mode
		checkboxChoice[1] = gd.getNextBoolean();		//Extended Kinetics
		checkboxChoice[2] = gd.getNextBoolean();		//Analyze all open Images

		guiValue[0] = (int)(1/tscan*100000);		//write values back into the int[] to save them back to disc
		guiValue[1] = (int)(psize*1000);
		guiValue[2] = (int)(cri*10);
		guiValue[3] = (int)(cri2*10);
		guiValue[4] = (int)nin;			//Number of Intervals
		guiValue[5] = (int)choicechooseFilter;
		guiValue[6] = (int)choiceoutputImg;
		guiValue[7] = (int)black; 			//Background

		if(checkboxChoice[0]==true) guiValue[8]=1;	//Ember Mode
		else guiValue[8]=0;

		if(checkboxChoice[1]==true) guiValue[9]=1;	//Extended Kinetics
		else guiValue[9]=0;

		if(checkboxChoice[2]==true) guiValue[10]=1;	//Analyze all open Images
		else guiValue[10]=0;

		//IJ.showMessage("box: "+checkboxChoice[2]+"        ");
		//IJ.showMessage("10: "+guiValue[10]+"     ");

		try
		{
			// write to options file SpMValuesV100.txt
			guiValue = schreiben(guiValue);
		}catch (FileNotFoundException e){
			System.out.println("file not found");
		}catch (IOException ioEx){
			System.out.println("IOException");
		}

		return;
	} // abbShowDialog

	public void run(ImageProcessor ip) {

		ProgressBar pb = null;		//Construct Progressbar.  Will only be used when "Ananlyze all open Images" is used.
		IJ.showProgress(10);		//Make sure that the ProgressBar is closed.  This is important when single images are analyzed

		// abb
		abbShowDialog();

		//
		int[] wList = WindowManager.getIDList();				//get list of open images
		int noOfImages = wList.length;					//No of images is number of elements in list
		//IJ.showMessage("Number of open images: "+noOfImages+" ");
		if (checkboxChoice[2] == false) noOfImages = 1;			//if only the active image should be analyzed, then number of images = 1

	for(int imageNo=0; imageNo<noOfImages; imageNo++){ 		//cycle through the open images
		ImagePlus activeImage = WindowManager.getImage(wList[imageNo]);	//imagePlus is next open image
		if (checkboxChoice[2] == true){
			title = activeImage.getTitle();		//Title of the ImagePlus
			ip = activeImage.getProcessor();
		}

		int width = ip.getWidth();
		int height = ip.getHeight();

		byte[] pix8 = new byte[width*height];				//Creates an int array
		short[] pix16 = new short[width*height];				//Creates a short array

		if(imageBit==0){
			//IJ.showMessage("This is an 8-bit image ");
			pix8 = (byte[])ip.getPixels();				//This is for 8 bit
		}

		if(imageBit==1){
			//IJ.showMessage("This is a 16 bit image");
			pix16 = (short[])ip.getPixels();				//This is for 16 bit
		}

		Rectangle r = ip.getRoi();
		int offset, j;

		String headings = "  #	   Ampl.	   FWHM	   FDHM	  fullWidth	  fullDur	   TtP	  \u0394(F/Fo)/\u0394t max	   Tau	  x-pos	  t-pos	 Analysis	 Parameters";		//Headings of result box
		if(checkboxChoice[1]==false)	headings="  #	   Ampl.	   FWHM	   FDHM	  x-pos	  t-pos	 Analysis	 Parameters";							//heading for normal kinetics

		if(imageNo==0){				//Do this only in the first round because it clears the results window.  Important for Analysis of all open Images
			IJ.setColumnHeadings(headings);
			IJ.showProgress(0);		//Initialize Progressbar here. This ensures that the first increase is shown.
		}


//		float[] flies = new float[pix.length];
		float[] flies = new float[width*height];

		if(imageBit==0){		//This is for 8 bit
			for (int y=r.y; y<(r.y+r.height); y++) {	//Berechnung des summenWertes und
				offset = y*width;						//kopieren des pixels[] in neu[]
				for (int x=r.x; x<(r.x+r.width); x++) {
					j = offset + x;
					flies[j]= 0xff & pix8[j];
				}
			}
		}

		if(imageBit==1){		//This is for 16 bit
			for (int y=r.y; y<(r.y+r.height); y++) {	//Berechnung des summenWertes und
				offset = y*width;						//kopieren des pixels[] in neu[]
				for (int x=r.x; x<(r.x+r.width); x++) {
					j = offset + x;
					flies[j]= 0xffff & pix16[j];
				}
			}
		}

		//Set Filter Kernels (xKernel and tKernel) according to GUI input
			int xKernel = 3;
			int tKernel = 3;

		if (choicechooseFilter==0){
			xKernel = 3;
			tKernel = 3;
		}
		else
			if (choicechooseFilter==1){
				xKernel = 5;
				tKernel = 5;
			}
			else
				if (choicechooseFilter==2){
					xKernel = 7;
					tKernel = 7;
				}
				else
					if (choicechooseFilter==3){	//For wavelet filter choose 5x5 Median afterwards
						xKernel = 5;
						tKernel = 5;
					}

//IJ.showMessage("xKernel: "+xKernel+"   ");

//		width = r.width;
//		height = r.height;

		int nx = width;
		int ny = height;
//IJ.write("nx= "+nx+"   ny= "+ny);


//****************************************
		float ima[] = new float[flies.length];
		// abb The output values ​​are saved in this array
		int abbMaxLCR = 10000;
		// abb was this
		//float tava[][] = new float[17][500];						//In diesem Array werden die Ausgabewerte gespeichert
		float tava[][] = new float[17][abbMaxLCR];					//In diesem Array werden die Ausgabewerte gespeichert
																	// The output values ​​are saved in this array
//float[] imc= new float[ima.length];
//imc = medianFilter(flies, height, width, xKernel, tKernel);

		if(choicechooseFilter==3){
			flies=waveletFilter(flies,height,width);
		}
//IJ.showMessage("min(flies): "+min(flies)+"   max(flies): "+max(flies)+" ");
		ima = medianFilter(flies, height, width, xKernel, tKernel);			//line 37: median filter to remove data points at extremes
//ima=(float[])flies.clone();
		int imaInt[] = new int[ima.length];		//Integerarray von ima anlegen
		for(int k=0; k<ima.length; k++){
			imaInt[k] = (int)ima[k];
		}
//IJ.showMessage("min(imaInt[]: "+min(imaInt)+" ");

		float imm[] = new float[ima.length];
		imm = (float[]) ima.clone();													//line 39


		float imb [] = new float[ima.length];
		int ss = 4;		//WAR 4
		int st = 4;

//float[] imc= new float[ima.length];
//imc = spatioTemporal(imaInt,height,width,ss,st);
		imb = spatioTemporal(imaInt,height,width,ss,st);

		float imageToShow [] = new float[ima.length];		//imageToShow is the image which is shown in the end

		if((choiceoutputImg == 0)|(choiceoutputImg == 1)){		//if outputImage should either be "Raw" or "Raw + Sparks"
			imageToShow = (float[])flies.clone();
		}

		if((choiceoutputImg == 2)|(choiceoutputImg == 3)){		//if outputImage should either be "Filtered" or "Filtered + Sparks"
			imageToShow = (float[])imb.clone();
		}



/////////////////////////////////////Muss diese schleife sein ?? division durch 1 JA!!!!!!! ima = imb
		for(int i=0; i<imb.length; i++){			//ima=imb/ct
			ima[i] = imb[i]/1;
		}
		imb = (float[]) ima.clone();			//imb=ima


		float a[] = new float[width];
		a = rebin1D(ima, height, width);

		int pr, pl;					//line 46
	//int black = 10;					//This value is detrmined in the GUI
		pr = edgeRight(a, black);
		pl = edgeLeft(a, black);
if(pl==0) pl = 1;
if(pr==width-1) pr=pr-1;



//IJ.showMessage("pl: "+pl+"   pr: "+pr+"   width: "+width+"    ");

if((pr-pl)<10){		//If the cellular width is too small show this
	IJ.showMessage("Error","The Background Value is too high.     ");
	return;
	}

//IJ.showMessage("total(ima)= "+total(ima)+"   stDev(ima)= "+stDev(ima)+"   ");

//		for(int i=0; i<a.length; i++){			//implements >black BUT THIS IS NOT IN THE ORIGINAL ALGORITHM
//			if(a[i]<black){			//all values <black are set to black
//				a[i]=9999999;
//			}
//		}



//float[] imc= new float[ima.length];
//imc = normalize(ima, height, width, a);
		ima = normalize(ima, height, width, a);

//IJ.showMessage("total(ima)= "+total(ima));
//IJ.showMessage("ima(2565)= "+ima[2565]);
//ima=edgeCare1(ima,height,width,pl+0,(width-pr+0),0,0);		//Fills non-cellular background with 1
//imb=edgeCare1(imb,height,width,pl+0,(width-pr+0),0,0);
//IJ.showMessage("ima(2565)= "+ima[2565]);
//imageToShow = (float[])ima.clone();
//IJ.showMessage("total(ima)= "+total(ima));
		float sd = 0;
		sd = stDevEdges(ima, height, width, pl+4, pr-4);									//line 50
//IJ.showMessage("stDevEdges(ima,height,width,"+(pl+4)+", "+(pr-4)+"): "+sd+"    ");


		float mask[] = new float[ima.length];		//Neues Array anlegen			//line 52
		mask = cutoff(ima, (float)1.0, (float)1.5, (float)sd);	//0005.tif			//Alle Pixel > mittel + Cri*stAbw auf 1 setzen
//		mask = medianFilter(mask, height, width, 5,5);	//0006.tif			//float mask[] is binary 1.0 or 0.0
////		mask = medianFilter(mask, height, width, xKernel,tKernel);	//0006.tif
		mask = liveOrDie(mask, height, width, 5, 13);
		mask = edgeCare(mask, height, width, 1, 1);	//fuellt Raender mit Nullen. Ansonsten koennte Spark am Rand detektiert werden, was zu Fehler bei Amplitude Berechnung fuehrt wg Mittelwert Berechnung


		for (int i=0; i<ima.length; i++){		//Excise potential spark region	/line 54
			ima[i]=imb[i]*(1-mask[i]);		//0007.tif
		}




//		float imr[] = new float[ima.length];
//		imr = (float[]) ima.clone();


//		float mar[] = new float[mask.length];
//		mar = (float[]) mask.clone();


		float rb55[] = new float[width];		//Zaehler aus Zeile 55
		rb55 = rebin1D(ima, height, width);


		float klammer[] = new float[mask.length];	//1.-float(mar) aus Zeile 55
		for (int i=0; i<mask.length; i++){
			klammer[i] = 1-mask[i];
		}

		float rbNenn[] = new float[width];
		rbNenn = rebin1D(klammer, height, width);//Nenner aus Zeile 55


		float bruch[] = new float[width];
		for (int i=0; i<bruch.length; i++){
			bruch[i] = rb55[i]/rbNenn[i];
		}


		float base[] = new float[width];
		base = smoothFilter(bruch, 1, width, 3,1);
//IJ.showMessage("base[173]= "+base[173]);


//		for(int i=0; i<base.length; i++){			//implements >black
//			if(base[i]<black){			//sets all values < black to black
//				base[i]=9999999;		//this is NOT in the original algorithm
//			}
//		}



//		float bbb=0;
//		bbb = stDevEdges(base, 1, width, 0, (width-1));


		imb = normalize(imb, height, width, base);//line 57	//0008.tif   This is the image without lines
imb=edgeCare1(imb,height,width,pl+0,(width-pr-1),0,0);	//fills area of non-cellular background with 1 ********************************************************************
		imm = (float[]) imb.clone();


//IJ.write("total(imm): "+total(imm)+"    ");
//			float testShow[] = new float[flies.length];
//			for(int i=0; i<testShow.length; i++){			//ima=ima*factorForOutput
//				testShow[i] = imb[i];
//			}



		if((choiceoutputImg == 4)|(choiceoutputImg == 5)){		//if outputImage should either be "F/Fo" or "F/Fo + Sparks"
			imageToShow = (float[])imb.clone();

			factorForOutput = 1;				//In case of F/Fo the imageToShow needs to be muliplied with a factor
								//factorForOutput is initialized in the very beginning to make it available in the end
			float maxInImage =  max(imageToShow);		//Detere the factor depending on max value in image
			if (maxInImage<2.5)
				factorForOutput = 100;
			else
				if((2.5<maxInImage)&(maxInImage<5))
					factorForOutput = 50;
				else
					if((5<maxInImage)&(maxInImage<10))
						factorForOutput = 25;
					else
						if(maxInImage>=10)
							factorForOutput = 12;

		if(imageBit==1) factorForOutput = 100;	//If 16 bit image then always factor = 100 because dynamic range large enough


			for(int i=0; i<imb.length; i++){			//ima=ima*factorForOutput
				imageToShow[i] = imageToShow[i]*factorForOutput;
			}
		}




////////////////////////////////
		if(imageBit==0){		//This is for 8-bit
			for (int y=r.y; y<(r.y+r.height); y++) {		//This shows the output image
				offset = y*width;
				for (int x=r.x; x<(r.x+r.width); x++) {
					j = offset + x;
					pix8[j] = (byte)imageToShow[j];		//This is for 8-bit
				}
			}
		}

		if(imageBit==1){		//This is for 16-bit
			for (int y=r.y; y<(r.y+r.height); y++) {		//This shows the output image
				offset = y*width;
				for (int x=r.x; x<(r.x+r.width); x++) {
					j = offset + x;
					pix16[j] = (short)imageToShow[j];
				}
			}
		}

		int minInImg = (int) min(imageToShow);		//Minimal and maximal value in the output image
		int maxInImg = (int) max(imageToShow);
		ip.setMinAndMax(minInImg, maxInImg);		//Adjust Brightness and Contrast according to min and max value in output image
////////////////////////////






//Select pulse region

		//int xmin = 0;
		int xmin = pl+4;
		//int xmax = width -1;
		int xmax = pr-4;
		int ml = 0;
		int nml = height -1;
//IJ.showMessage("pulse region: "+xmin+"   "+xmax+"   "+ml+"   "+nml+"   ");

		int npy = nml-ml+1;

		//int  nin = 3;		//Number of intervals subdividing pulse WIRD AM ANFANG ANGELEGT
		if (nin == 0){
			nin = 5;
		}

		int ninc=(int)(Math.ceil((float)npy/(float)nin));

//IJ.write("npy: "+npy+"   nin: "+nin+"   ninc: "+ninc+"   ");


		int skc = 0;		//Sparkscounter

//For Next
for (int jin=0; jin<nin; jin++){
		//TODO: stDevEdges fuer variable Werte anpassen
		//+++sd = stDevEdges(imb, height, width, 0, (width-1));	//Parameter 0,(width-1) ist Spezialfall wenn in "Select pulse region" das gesamte Bild gewaehlt wird

		int kk1 = ml+(jin+1)*ninc-1;	//kk1 ist bottomEdge von imbKlammer
			if(kk1 > nml){
				kk1 = nml;
			}


		float imbKlammer[] = new float[(xmax-xmin+1)*(kk1-(ml+jin*ninc)+1)];
		imbKlammer = arrayCopy(imb, height, width, xmin, xmax, (ml+jin*ninc),kk1);

		sd = (float)stDev(imbKlammer);

		float mean;

		mean = mittel(imbKlammer);


//IJ.showMessage("sd: "+sd+" mean: "+mean+" ");




		//TODO: anpassen
		//+++mask = cutoff(imb, mean, 2, (float)sd);		//Alle Pixel > mean + 2*sd auf 1 setzen
		//+++mask = medianFilter(mask, height, width, 5,5);	//0015.tif

		for (int i=0; i<mask.length; i++){		//mask[] mit 0 fuellen
			mask[i] = 0;
		}

		for (int i=0; i<imbKlammer.length; i++){	//Alle Pixel in imbKlammer > mean + 2*sd auf 1 setzen
			if(imbKlammer[i]>(mean + 2*sd)){
				mask[i] = 1;
			}
		}

//		mask = medianFilter(mask, height, width, 5,5);	//0015.tif THIS IS CORRECT
////		mask = medianFilter(mask, height, width, xKernel,tKernel);	//0015.tif
		mask = liveOrDie(mask, height, width, 5, 13);		//This fills holes and removes small islets in the mask
							//mask for potential spark regions >m+2SD
//			for(int i=0; i<imageToShow.length; i++){			//ima=ima*factorForOutput
//				imageToShow[i] = mask[i];
//			}





		float tem[] = new float[(xmax-xmin+1)*(kk1-(jin*ninc)+1)];
		float imbTem[] = new float[(xmax-xmin+1)*(kk1-(jin*ninc)+1)];
//		float maskTem[] = new float[(xmax-xmin+1)*(kk1-(jin*ninc)+1)];		//Taken out in version 38 because not needed anymore

		imbTem = arrayCopy(imb, height, width, xmin, xmax, jin*ninc, kk1);
//		maskTem = arrayCopy(mask, height, width, xmin, xmax, jin*ninc, kk1);		//It was previously needed in the following loop but this was incorrect

		//+++float tem[] = new float[mask.length];
		for (int i=0; i<imbTem.length; i++){		//
			tem[i]=imbTem[i]*(1-mask[i]);		//0016.tif
		}
//IJ.write("total(tem): "+total(tem)+"    ");


		int zaehler =0;
		for (int i=0; i<tem.length; i++){			//implementation of (where tem gt 0.)
			if(tem[i]==0){
			zaehler = zaehler +1;	//zaehlt Pixel, die =0 sind
			}
		}

		float temGT0[] = new float[(tem.length-zaehler)];	//neues Array, das nur die Pixel von tem enthaelt, die groesser 0 sind
		int k=0;
		for (int i=0; i<tem.length; i++){		//
			if(tem[i]>0){
				temGT0[k] = tem[i];
				k = k+1;
			}
		}

		sd = (float)stDev(temGT0);		//This is the SD and the mean of the image without regions >mean + 2*SD (i.e. without potential spark regions)
		mean = mittel(temGT0);
//IJ.write("mean= "+mean+"   SD= "+sd+" ");


		int im[] = new int[imb.length];
		float imZwischen[] = new float[im.length];
		float zwischen;
		for (int i=0; i<im.length; i++){			//implementation of (where tem gt 0.)
			zwischen = (imb[i] - (mean+cri*sd))*100000;
				if(zwischen<0){
				zwischen = 0;
				}
				if(zwischen>1){
				zwischen = 1;
				}
			imZwischen[i] = zwischen;			//imZwischen[i] is 0017a.tif
		}

//		imZwischen = medianFilter(imZwischen, height, width, 5, 5);
////		imZwischen = medianFilter(imZwischen, height, width, xKernel, tKernel);
		imZwischen = liveOrDie(imZwischen, height, width, 5, 13);


		for (int i=0; i<im.length; i++){		//
			im[i] = (int)imZwischen[i];			//im[i] is 0017b THIS IS CORRECT
		}
//IJ.write("total(im) VOR edgeCare: "+total(im)+"     ");




		im = edgeCare(im, height, width, ss/2+1, st/2+1);	//fuellt Raender mit Nullen wg. smoothing	//This is 0017.tif line 68
//		im = edgeCare(im, height, width, (int)(xKernel/2+1), (int)(tKernel/2+1));	//fuellt Raender mit Nullen wg. smoothing

//IJ.write("ss/2: "+(ss/2)+"  st/2: "+(st/2)+"       ");
//IJ.write("total(im) NACH edgeCare: "+total(im)+"     ");


//---------------------------
	//***************ACHTUNG: Liefert nicht exakt die gleichen Ergebnisse
		int ime[] = new int[imb.length];
		for (int i=0; i<ime.length; i++){			//implementation of (where tem gt 0.)
			zwischen = (imb[i] - (mean+cri2*sd))*100000;
				if(zwischen<0){
				zwischen = 0;
				}
				if(zwischen>1){
				zwischen = 1;
				}
			imZwischen[i] = zwischen;
		}

//		imZwischen = medianFilter(imZwischen, height, width, 5, 5);
////		imZwischen = medianFilter(imZwischen, height, width, xKernel, tKernel);
		imZwischen = liveOrDie(imZwischen, height, width, 5, 13);


		for (int i=0; i<ime.length; i++){		//
			ime[i] = (int)imZwischen[i];
		}

		ime = edgeCare(ime, height, width, ss/2+1, (st/2 +1));	//fuellt Raender mit Nullen wg. smoothing THIS IS 0018.tif    2SD Image
//		ime = edgeCare(ime, height, width, (int)(xKernel/2+1), (int)(tKernel/2 +1));	//fuellt Raender mit Nullen wg. smoothing
//-------------------------------

//IJ.write("total(ime) after edgCare: "+total(ime));

		int imf[] = new int[ime.length];
		imf = (int[]) ime.clone();				//line 73


		imb = (float[]) imm.clone();				//line 74 imb will be used for spark measurement




//THE INPUT ARAY FOR THE DENSITY FILTER HAS TO BE im (0017.tif)

//			for(int i=0; i<imageToShow.length; i++){			//ima=ima*factorForOutput
//				imageToShow[i] = ime[i];
//			}
////////////////////////////////
//		for (int y=r.y; y<(r.y+r.height); y++) {		//This shows the output image
//			offset = y*width;
//			for (int x=r.x; x<(r.x+r.width); x++) {
//				j = offset + x;
//				pix[j] = (byte)imageToShow[j];
//			}
//		}
//
//			minInImg = (int) min(imageToShow);		//Minimal and maximal value in the output image
//			maxInImg = (int) max(imageToShow);
//		ip.setMinAndMax(minInImg, maxInImg);		//Adjust Brightness and Contrast according to min and max value in output image
////////////////////////////








//jump1:			//wird vom Userinterface aufgerufen
		ime = (int[])imf.clone();				//line 83

		int imaux[] = new int[im.length];
		//+++imaux = (int[]) im.clone();				//0019.tif //Ist Spezialfall fuer gesamtes Bild

		int imCopy[] = new int[(xmax-xmin+1)*(kk1-(ml+jin*ninc)+1)];
		imCopy = arrayCopy(im,height, width, xmin, xmax, (ml+jin*ninc),kk1);
//IJ.showMessage("total(imCopy): "+total(imCopy)+"      ");


//		imaux = arrayPaste(arrayCopy(im,height, width, xmin, xmax, (ml+jin*ninc),kk1),(kk1-(ml+jin*ninc)+1),(xmax-xmin+1),imaux, height, width,(ml+jin*ninc),kk1);
		imaux = arrayPaste(imCopy, (kk1-(ml+jin*ninc)+1), (xmax-xmin+1), imaux, height, width, (ml+jin*ninc), xmin);






		while(total(imaux) != 0){

			int A = 0;
			for(int i = 0; i<imaux.length; i++){
				if(imaux[i]>0){
					A = i;
					break;
				}
			}
//IJ.showMessage("a= "+A);

			int tt;
			tt = A/nx;

			int xx;
			xx = A%nx;
//IJ.write("a= "+A);
//IJ.write("tt= "+tt+"     xx= "+xx+"       ");

			//Define search area
			int nnl;
			if((6/psize < xx)){
				nnl = (int)(6/psize);
			}
			else{
				nnl = xx;
			}

			int nnr;
			if(6/psize < (nx-xx-1)){
				nnr = (int)(6/psize);
			}
			else{
				nnr = nx-xx-1;
			}

			int maxLengthOfEvents = 250;				//max Length of detected events is 250 ms in normal mode
			if(checkboxChoice[0]==true) maxLengthOfEvents=2500;	//if Ember mode then 2500 ms

			int mmb;
			if(maxLengthOfEvents/tscan < tt){
				mmb = (int)(maxLengthOfEvents/tscan);
			}
			else{
				mmb = tt;
			}

			int mme;
			if(maxLengthOfEvents/tscan < (ny-tt-1)){
				mme = (int)(maxLengthOfEvents/tscan);
			}
			else{
				mme = ny-tt-1;
			}
//IJ.write("nnl= "+nnl+"   nnr= "+nnr+"  mmb= "+mmb+"  mme= "+mme+"    ");
//IJ.write("250./tscan= "+(250/tscan)+"   ny= "+ny+"   tt="+tt+"   ");
			int ymWidth = (nnl+nnr+1);
			int ymHeight = (mmb+mme+1);
//IJ.write("ymWidth:  "+ymWidth+"         ymHeigh:   "+ymHeight+"      ");


			int ym[] = new int[ymWidth*ymHeight];	// array to hold growing points
			ym[nnl+mmb*ymWidth] = 1;		// initial seeding for growth
			//ym[0] = 1;			// 0021.tif

//int test[] = new int[ima.length];

//test = transform(ym, ymHeight, ymWidth, height, width);
//IJ.showMessage("total(test)= "+total(test)+"        ");


			int sk[] = new int[ym.length];
			sk = (int[]) ym.clone();

			int yt[] = new int[sk.length];
//IJ.write("Vor for-Schleife total(sk): "+total(sk)+"    ");
//IJ.write("Vor for-Schleife total(ime): "+total(ime)+"     ");

			for(int iii=0; iii<500; iii++){
				yt = (int[]) sk.clone();
// abb start of for loop
//IJ.write("Anfang for-Schleife total(yt): "+total(yt)+"     ");
//IJ.write("Anfang for-Schleife total(ime): "+total(ime)+"     ");

				//potential new surface points
				int ynLeftEdge = xx-nnl;
				int ynRightEdge = xx+nnr;
				int ynTopEdge = tt-mmb;
				int ynBottomEdge = tt+mme;
				int ynWidth = (ynRightEdge-ynLeftEdge+1);
				int ynHeight = (ynBottomEdge-ynTopEdge+1);
//IJ.showMessage("tt:  "+tt+"    ");
				int ynKlammer[] = new int[ynWidth*ynHeight];
				ynKlammer = arrayCopy(ime, height, width, ynLeftEdge, ynRightEdge, ynTopEdge, ynBottomEdge);

//IJ.showMessage("ynKlammer total= "+total(ynKlammer)+"   mittel= "+mittel(ynKlammer)+"   width: "+(ynRightEdge-ynLeftEdge+1)+"      height: "+(ynBottomEdge-ynTopEdge+1)+"        length :  "+ynKlammer.length+"                ");
//test = transform(ynKlammer, (ynBottomEdge-ynTopEdge+1),(ynRightEdge-ynLeftEdge+1),height,width);


				float ymFloat[] = new float[ym.length];		//int Array ym auf float casten
				int ymFix[] = new int[ym.length];			//gesmoothtes Arra auf int casten

				for (int i=0; i<ym.length; i++){			//int Array ym auf float casten
					ymFloat[i] = (float)ym[i];
				}

				ymFloat = smoothFilter(ymFloat, ymHeight, ymWidth, 3, 3);	//3x3 smoothing Filter

				for (int i=0; i<ymFloat.length; i++){
					ymFix[i] = (int)(ymFloat[i]*100);
					if (ymFix[i]>1){	//implementation of <1
						ymFix[i] = 1;
					}
				}
//IJ.showMessage("ymFix total= "+total(ymFix)+"   mittel= "+mittel(ymFix)+"   length:     "+ymFix.length+"       ");

				boolean ynKlammerBoolean[] = new boolean[ynKlammer.length];	//ynKlammer auf boolean casten, da AND sonst nicht fkt
				for (int i=0; i<ynKlammer.length; i++){
					if(ynKlammer[i]  != 0){
						ynKlammerBoolean[i] = true;
//IJ.showMessage("ynKlammerBoolean["+i+"]= "+ynKlammer[i]+"    ");
					}
				//	else{
				//		ynKlammerBoolean[i] = false;
				//	}
				}

				boolean ymFixBoolean[] = new boolean[ymFix.length];			//ymFix auf boolean casten
				for (int i=0; i<ymFix.length; i++){
					if(ymFix[i] != 0){
						ymFixBoolean[i] = true;
//IJ.showMessage("ymFixBoolean["+i+"]= "+ymFix[i]+"    ");
					}
				//	else{
				//		ymFixBoolean[i] = false;
				//	}
				}


				int yn[] = new int[ynKlammer.length];				//logische UND Verknuepfung
				for (int i=0; i<ynKlammer.length; i++){
					if (ynKlammerBoolean[i] && ymFixBoolean[i]){
						yn[i] = 1;
					}
				}

//test = transform(yn, (ynBottomEdge-ynTopEdge+1),(ynRightEdge-ynLeftEdge+1),height,width);


				//no further growth, stop and calculate the parameters
//IJ.showMessage("total(yn)= "+total(yn));
				if (total(yn)==0){
					break;
				}


				//update sk
				for (int i=0; i<sk.length; i++){
					if (sk[i] < yn[i]){
						sk[i] = yn[i];
					}
				}
//IJ.showMessage("sk total= "+total(sk)+"   mittel= "+mittel(sk)+"           ");

				//excise the points which are already included in the cluster
				int cutOut[] = new int[ynWidth*ynHeight];	//Zwischenspeicher

				///	ime
				cutOut = arrayCopy(ime, height, width, ynLeftEdge, ynRightEdge, ynTopEdge, ynBottomEdge);

				for (int i=0; i<cutOut.length; i++){
					cutOut[i] = cutOut[i] - sk[i];
					if (cutOut[i] < 0){
						cutOut[i] = 0;
					}
				}
				//System.out.println("abb cutOut ynTopEdge:" + ynTopEdge + " ynLeftEdge:" + ynLeftEdge);
				ime = arrayPaste(cutOut, ynHeight, ynWidth, ime, height, width, ynTopEdge, ynLeftEdge);
// middle for loop
//IJ.write("Mitte for-Schleife total(ime): "+total(ime)+"    ");


				///	im
				cutOut = arrayCopy(im, height, width, ynLeftEdge, ynRightEdge, ynTopEdge, ynBottomEdge);

				for (int i=0; i<cutOut.length; i++){
					cutOut[i] = cutOut[i] - sk[i];
					if (cutOut[i] < 0){
						cutOut[i] = 0;
					}
				}
				im = arrayPaste(cutOut, ynHeight, ynWidth, im, height, width, ynTopEdge, ynLeftEdge);

				/// imaux
				cutOut = arrayCopy(imaux, height, width, ynLeftEdge, ynRightEdge, ynTopEdge, ynBottomEdge);

				for (int i=0; i<cutOut.length; i++){
					cutOut[i] = cutOut[i] - sk[i];
					if (cutOut[i] < 0){
						cutOut[i] = 0;
					}
				}
				imaux = arrayPaste(cutOut, ynHeight, ynWidth, imaux, height, width, ynTopEdge, ynLeftEdge);
//IJ.write("Mitte for-Schleife total(imaux): "+total(imaux)+"      ");

				//true new surface point
				for (int i=0; i<ym.length; i++){
					ym[i] = yn[i] - yt[i];
					if(ym[i]<0){
						ym[i] = 0;
					}
				}

				if (iii == 500){
					IJ.showMessage("WARNING: SPARK SEARCH AREA MAY BE TOO SMALL  ");
				}
			}

			skc = skc + 1;

			//spark measurement
//			int pixels = total(sk);
			//time position
			float aTime[] = new float[mmb+mme+1];

			float skFloat[] = new float[sk.length];
			for (int i=0; i<sk.length; i++){
				skFloat[i] = (float)sk[i];
			}

			aTime = rebinZeile(skFloat, ymHeight, ymWidth);		//sk[] hat die gleichen Dimensionen wie ym[]
//IJ.showMessage("total(aTime)= "+total(aTime)+"               ");

			int aa[] = new int[whereZaehler(aTime, "ne", 0)]; 	//Array fuer folgenden 'where' Vergleich anlegen
			aa = where(aTime, "ne", 0);			//Alle Positionen in a schreiben, die in aTime != 0 sind
//IJ.showMessage("aa:  "+ aa[0]+"   "+ aa[1]+"   "+ aa[2]+"   "+ aa[3]+"   "+ aa[4]+"   "+ aa[5]+"     ");

			int tpos = tt - mmb + min(aa);
			int durmax = max(aa) - min(aa) + 1;
			int at = max(aa);
			int bt = min(aa);
//IJ.write("tpos: "+tpos+"       durmax: "+durmax+"       at: "+at+"   bt: "+bt+"          ");


			//x coordinate

			float aXCoor[] = new float[nnl+nnr+1];
			aXCoor = rebin1D(skFloat, ymHeight, ymWidth);

			int aXX[] = new int[whereZaehler(aXCoor, "ne", 0)];
			aXX = where(aXCoor, "ne", 0);

			float xpos = xx - nnl +(float)(max(aXX)+min(aXX))/2;
//IJ.showMessage("xx: "+xx+"    nnl: "+nnl+"       (max(aXX)+min(aXX))/2: "+(max(aXX)+min(aXX))/2+"                        ");
			int ax = max(aXX);
			int bx = min(aXX);
			int breadthm = max(aXX) - min(aXX) +1;

//			float averdur = (float)pixels /(float) breadthm;
//			float averwid = (float)pixels / (float)durmax;
//IJ.write("pixels: "+pixels+"             ");
//IJ.write("xpos: "+xpos+"       ax: "+ax+"   bx: "+bx+"   breadthm: "+breadthm+"       averdur: "+averdur+"          averwid:"+averwid+"               ");

			int wLeftEdge = xx-nnl;
			int wRightEdge = xx+nnr;
			int wTopEdge = tt-mmb;
			int wBottomEdge = tt+mme;
			int wWidth = (wRightEdge-wLeftEdge+1);
			int wHeight = (wBottomEdge-wTopEdge+1);

//IJ.write("wLeftEdge: "+wLeftEdge+"  ");

			float w[] = new float[wWidth*wHeight];
//IJ.write("w.length: "+w.length);
//IJ.write("total(imb): "+total(imb));
			w = arrayCopy(imb, height, width, wLeftEdge, wRightEdge, wTopEdge, wBottomEdge);

			for (int i=0; i<w.length; i++){
				w[i] = w[i] * sk[i];
			}
//float testFloat[] = new float[height*width];
//testFloat = transform(w, (wBottomEdge-wTopEdge+1),(wRightEdge-wLeftEdge+1),height,width);

//			float peak = max(w) - mean;
//IJ.write("max(w): "+max(w)+"   peak: "+peak+"     mean: "+mean+"     ");

			//int pPosition[] = new int[whereZaehler(w, "eq", (peak+mean))];*********Hier sind Rundungsfehler aufgetreten
			int pPosition[] = new int[whereZaehler(w, "eq", (max(w)))];
//IJ.write("w(13934): "+w[13934]);
//IJ.write("pPosition[length]: "+pPosition.length+"    ");
			//pPosition = where(w, "eq", (peak+mean));**********Hier sind Rundungsfehler aufgetreten
			pPosition = where(w, "eq", (max(w)));
//IJ.write("total(w): "+total(w));
//IJ.write("NOTE VOR");
//IJ.write("p: "+pPosition[0]+"  ");
//IJ.write("NOTE MITTE");
			float p = pPosition[0];
//IJ.write("NOTE NACH");
			int xxx = (int)(p % (nnl + nnr + 1));

			int ttt = (int)(p / (float)(nnl+nnr+1));
//IJ.write("peak: "+peak+"   p: "+p+"     xxx: "+xxx+"       ttt: "+ttt+"           ");
//IJ.showMessage("(tt-mmb+ttt):  "+(tt-mmb+ttt)+"   ");
			float averp = total(arrayCopy(imb, height, width, (xx-nnl+xxx-1), (xx+xxx-nnl+1),(tt-mmb+ttt-1),(tt-mmb+ttt+1)))/9 - mean;
//IJ.write("averp: "+averp+"        ");

//			float amp = total(w) / pixels;		//average amplitude
//IJ.write("amp: "+amp+"        ");





			//amplitude,duration and width measured as usual

			int k1 = (int)(xx-nnl+xxx-(2/psize));
				if(k1<0){
					k1 = 0;
				}

			int k2 = (int)(xx-nnl+xxx+(2/psize)-1);
				if(k2 > (nx-0)){
					k2 = (nx-0);
				}

			int k3 = (tt-mmb+ttt-1);
			int k4 = (tt-mmb+ttt+1);

			int k5 = (int)(xx-nnl+xxx+(2/psize)-1);
				if (k5>(nx-0)){
					k5 = (nx-0);
				}

			int k6 = (int)(xx-nnl+xxx-2/psize);
				if (k6<0){
					k6=0;
				}

//IJ.write("xx: "+xx+" nnl: "+nnl+" xxx: "+xxx+" 2./psize: "+(2/psize)+" ");




			float wK[] = new float[(k5-k6+1)];


			//Dies ist die kuerzere Variante
			//wK is the profile from which the FWHM is calculated. It is only as wide as the total width of the spark.
			//wK = rebin1D((arrayCopy(imb, height, width, k1, k2, k3, k4)), (k4-k3+1), (k2-k1+1));
			wK = rebin1D((arrayCopy(imb, height, width, (xx-nnl+bx), (xx-nnl+ax), k3, k4)), (k4-k3+1), ((xx-nnl+ax)-(xx-nnl+bx)+1));
//for(int i=0; i<wK.length; i++){
//	IJ.write(wK[i]+"   ");
//}
//IJ.write("k1: "+k1+"    k2: "+k2+"    k3: "+k3+"    k4: "+k4+"    k5: "+k5+"    k6: "+k6+"           ");
//IJ.write("left edge: "+(xx-nnl+bx));
//IJ.write("right edge: "+(xx-nnl+ax));

			//float pw = max(wK);	//This calculates the peak value from the newly generated array

			float pw = averp+1;	//This is the peak value as it appears in the output datatable
//IJ.write("pw: "+pw+"   ");

			int w50 = whereZaehler(wK, "ge", (pw+1)/2);
//IJ.write("w50: "+w50+" ");

			int vgl = 0;	//Vergleichsvariable

			k1 = (int)(xx-nnl+xxx-(0.4/psize));
			if(k1<0){
				k1 = 0;
			}

			k2 = (int)(xx-nnl+xxx+(0.4/psize)-1);
			if(k2>(nx-0)){
				k2 = (nx-0);
			}

			k3 = (int)(tt-mmb);
			vgl = (int)(tt-mmb+ttt-30/tscan);
				if (vgl<0){
					vgl = 0;
				}
			if (k3 > vgl){
				k3 = vgl;
			}

			k4 = (int)(tt+mme);
			vgl = (int)(tt-mme+ttt+50/tscan -1);
				if (vgl > ny){
					vgl = ny;
				}
			if (k4 < vgl){
				k4 = vgl-1;
			}

			k5 = (int)(tt+mme);
			vgl = (int)(tt-mmb+ttt+50/tscan -1);
				if (vgl > ny){
					vgl = ny;
				}
			if (k5 < vgl){
				k5 = vgl-1;
			}

			k6 = (int)(tt-mmb);
			vgl = (int)(tt-mmb+ttt-30/tscan);
				if (vgl<0){
					vgl = 0;
				}
			if (k6 > vgl){
				k6 = vgl;
			}
/*
IJ.write("k1: "+k1+"    k2: "+k2+"    k3: "+k3+"    k4: "+k4+"    k5: "+k5+"    k6: "+k6+"           ");
IJ.write("k4-k3+1: "+(k4-k3+1));
IJ.write("k2-k1+1: "+(k2-k1+1));
IJ.write(" ");


IJ.write("tpos: "+tpos+"     durmax: "+durmax);
IJ.write("xpos: "+xpos);
IJ.write(" ");
*/


//			float imbK2[] = new float[(k2-k1+1)*(k4-k3+1)];
//			imbK2 = arrayCopy(imb, height, width, k1, k2, k3, k4);

////////////////////////	float wK2[] = new float[(k5-k6+1)];
			float wK2[] = new float[(durmax+1)];

//			wK2 = rebinZeile(imbK2, (k4-k3+1), (k2-k1+1));

			//Dies ist die kuerzere Variante
//////////////////////		wK2 = rebinZeile((arrayCopy(imb, height, width, k1, k2, k3, k4)), (k4-k3+1), (k2-k1+1)); This is the original line but the array is way to long (even longer than the total length of the event)
//IJ.showMessage("Vor");
			wK2 = rebinZeile((arrayCopy(imb, height, width, k1, k2, tpos,tpos + durmax)), (tpos+durmax-tpos+1), (k2-k1+1));
//IJ.showMessage("Nach");

//___________________________________________________________)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
//for(int i=0; i<wK2.length; i++){
//	IJ.write(wK2[i]+"   ");
//}


//			float pk = max(wK2);
//IJ.write("pk: "+pk+"                   ");

			int d50 = whereZaehler(wK2, "ge", (pw+1)/2);
//IJ.write("d50: "+d50+"               ");
//IJ.write("pw: "+pw);
//IJ.write("(pw+1)/2:  "+(pw+1)/2+"   ");


			int ii = skc;	// ii is initialized here in order to be applicable during the calculation of tau

//For max deltaF/Fo use the wk2 array up to peak



			if(checkboxChoice[1]==true){	//Here starts the calculation of the time-constant of the decline
				int TPeak = tt-mmb+ttt;				//position of peak
				int TEnd = tt-mmb+at;				//position of end
				int Duration = TEnd-TPeak+1;		//duration of decline THIS IS NOT THE TOTAL DURATION
				int upstrokeDuration = (tt-mmb+ttt-tpos)+1;	//duration of upstroke

				float decline[] = new float[Duration];	//This array holds only the decline of the spark
				float upstroke[] = new float[upstrokeDuration];//This array holds only the upstroke of the spark

				for(int i=0; i<decline.length; i++){			//copy the decay part of the total spark into the decline array
					decline[i] = wK2[i+((tt-mmb+ttt)-(tpos))];	//((tt-mmb+ttt)-(tpos)) is Time-to-Peak
				}

				for(int i=0; i<(upstrokeDuration); i++){			//copy the upstroke part of the total spark into the upstroke array
					upstroke[i] = wK2[i];
				}
//	IJ.write("upstroke length: "+upstrokeDuration);
//	IJ.write("decline length: "+decline.length);
//	IJ.write("TPeak: "+TPeak);
//	IJ.write("TEnd: "+TEnd);

				float Plateau;	//this is the Plateau of the decline

				//if(Duration<4) Plateau=100;		//if the total duration of the decline array is less then 4 then set Plateau to 100
				//else{
				//	Plateau = (decline[Duration-1]+decline[Duration-2]+decline[Duration-3])/3;	//average of the last 3 values in the array
				//}
				Plateau = 1;	//Plateau is always 1 = background. All sparks decline to the background level
//IJ.write("Plateau: "+Plateau);

//IJ.write(" ");
//IJ.write(" ");
//for(int i=0; i<upstrokeDuration; i++){
//	IJ.write(upstroke[i]+"   ");
//}
//IJ.write(" ");
//for(int i=0; i<wK2.length; i++){
//	IJ.write(wK2[i]+"   ");
//}
//for(int i=0; i<decline.length; i++){
//	IJ.write(decline[i]+"   ");
//}

				double xData[] = new double[decline.length];	//These are the arrays for the CurveFitter
				double yData[] = new double[decline.length];

				for(int i=0; i<decline.length; i++){
					xData[i]=i*tscan;				//xData is time axis in msec
					yData[i]=decline[i]-Plateau;	//yData is the Plateau corrected decline array
				}

				CurveFitter cf = new CurveFitter(xData,yData);	//Constructs a new CurveFitter
				cf.doFit(4);			//Starts curvefit. 4=exponential

				double[] fitResults = cf.getParams();
				fitResults[1]=Math.abs(1/fitResults[1]);	//transform k to tau
//IJ.write("tau: "+fitResults[1]);


				//This is about the steepness
				float[] upstrokeSteepness = new float[upstrokeDuration-1];	//this array holds the steepness of the upstroke


					for (int i=0; i<upstrokeDuration-1; i++){		//calculate the steepness of the upstroke
						upstrokeSteepness[i] = (upstroke[i+1]-upstroke[i])/tscan;
					}

					float maxSteepness = max(upstrokeSteepness)*1000;	//max value in the upstrokeSteepness array



				tava[15][ii] = (float)fitResults[1];
				tava[16][ii] = maxSteepness;
			}		//end of the extended Analysis

//IJ.write("(xx-nnl): "+(xx-nnl+bx));

			tava[0][ii] = averp;			//amplitude (F/Fo)

			tava[1][ii] = w50 * psize;		//FWHM
			tava[2][ii] = d50 * tscan;		//FDHM


//			tava[1][ii] = averwid * psize;		//FWHM
//			tava[2][ii] = averdur * tscan;		//FDHM
			tava[3][ii] = xpos * psize;		//xpos				//This is the x-pos of the middle of the spark
			tava[4][ii] = (tpos+(tt-mmb+ttt)-(tpos)) * tscan;		//tpos				//This is the t-position of the beginning of the spark
			tava[5][ii] = durmax * tscan;		//full duration of spark		***********************************
			tava[6][ii] = breadthm * psize;		//full width of spark	***********************************
			tava[7][ii] = xx-nnl;			//left edge
			tava[8][ii] = tt-mmb;			//right edge
			tava[9][ii] = bx;
			tava[10][ii] = ax;
			tava[11][ii] = bt;
			tava[12][ii] = at;
			tava[14][ii] = ((tt-mmb+ttt)-(tpos))*tscan;	//Time to Peak

//	(tt-mmb+bt) is the t-position of the beginning of the spark (as is tpos)

//IJ.showMessage("tava[6][ii]:  "+tava[6][ii]+"   ");

			boolean doppelt = false;	//flag for detected double spark

			for(int i=0; i<ii; i++){	//Sparks, die vollstaendig IM Kasten von VORHERIGEN Sparks liegen ausschliessen

//IJ.showMessage("tava[3]["+ii+"]: "+tava[3][ii]+" (tava[3]["+i+"]-tava[1]["+i+"]/2): "+(tava[3][i]-tava[1][i]/2)+"                     ");

				if
				( 					//&& is AND
				//(tava[3][ii] >= (tava[3][i]-tava[1][i]/2) ) && 		//xpos
				//(tava[3][ii] <= (tava[3][i]+tava[1][i]/2)) && 		//xpos
				(tava[3][ii] >= (tava[3][i]-tava[6][i]/2) ) && 		//xpos
				(tava[3][ii] <= (tava[3][i]+tava[6][i]/2)) && 		//xpos
				(tava[4][ii] >= tava[4][i] ) && 			//tpos
				((tava[4][ii]+tava[5][ii]) < (tava[4][i]+tava[5][i])) 		//tpos
				//(tava[4][ii] <=(tava[4][i]+tava[2][i])) 		//tpos
				)
				{
					tava[0][ii]=0;			//remove spark
					/*tava[1][ii]=0;
					tava[2][ii]=0;
					tava[3][ii]=0;
					tava[4][ii]=0;
					tava[5][ii]=0;
					tava[6][ii]=0;
					tava[7][ii]=0;
					tava[8][ii]=0;*/

					skc = skc - 1;
					ii = ii - 1;
					doppelt  = true;	//set flag
//IJ.showMessage("Erste Schleife");
				}
			}

			if(doppelt == false){			//do this only if spark is not already detected as double spark
				for(int i=0; i<ii; i++){	//Sparks, die einen VORHERIGEN Spark komplett beinhalten behalten und kleineren loeschen
					//IJ.show
					//IJ.showMessage("(tava[3][ii] >= (tava[3][i]-tava[1][i]/2): "+tava[3][ii]+"             "+(tava[3][i]-tava[1][i]/2)+"                   ");
					if(
					(tava[3][ii] >= (tava[3][i]-tava[1][i]/2) ) &&
					(tava[3][ii] <= (tava[3][i]+tava[1][i]/2)) &&
					(tava[4][ii] <= tava[4][i] ) &&
					( (tava[4][ii]+tava[2][ii]) >= (tava[4][i]+0)) )
					{
//IJ.showMessage("Spark No. "+i+" liegt in Spark No. "+ii+"   ");
						tava[0][i]=0;		//overwrite parameters of included spark with 0
						tava[1][i]=0;
						tava[2][i]=0;
						tava[3][i]=0;
						tava[4][i]=0;
						tava[5][i]=0;
						tava[6][i]=0;
						tava[7][i]=0;
						tava[8][i]=0;
						tava[9][i]=0;
						tava[10][i]=0;
						tava[11][i]=0;
						tava[12][i]=0;
						tava[13][i]=0;
						tava[14][i]=0;
						tava[15][i]=0;
						tava[16][i]=0;
					}
				}
			}

			String sparkNo = String.valueOf(ii);			//Preliminary spark parameter output during calculation
			String amplitude = IJ.d2s(tava[0][ii],3);			//otherwise the user might think the program has crashed
			String halfWidth = IJ.d2s(tava[1][ii],2);
			String halfDur = IJ.d2s(tava[2][ii],2);
			String xPos = IJ.d2s(tava[3][ii],2);
			String yPos = IJ.d2s((tava[4][ii]/1000),3);
			String fullDur = IJ.d2s(tava[5][ii],2);
			String fullWidth = IJ.d2s(tava[6][ii],2);
			String TtP = IJ.d2s(tava[14][ii],2);
			String Tau = IJ.d2s(tava[15][ii],2);
			String FF0max = IJ.d2s(tava[16][ii],2);

			if(tava[14][ii]==0) {			//if Time-to-Peak is 0 then empty output for TtP and FF0max
				TtP="";
				FF0max = "";
			}

//IJ.showMessage("fullWidth:   "+fullWidth+"   ");

//TODO: different output depending on whether extended kinetics or not

if(checkboxChoice[2]==false){		//Output of intermediate results only when single images are analyzed
	if (doppelt != true){
		if (checkboxChoice[1]==true)			//if extended kinetics then output of all parameters
			IJ.write(sparkNo+"	 "+amplitude+ "	"+halfWidth+"	"+halfDur+"	"+fullWidth+"	"+fullDur+"	"+TtP+"	"+FF0max+"	"+Tau+"	"+xPos+"	"+yPos+"   ");
		else
			IJ.write(sparkNo+"	 "+amplitude+ "	"+halfWidth+"	"+halfDur+"	"+xPos+"	"+yPos+"   ");
}




/*
	if((choiceoutputImg == 1)|(choiceoutputImg == 3)|(choiceoutputImg == 5))		//if outputImage should be "... + Sparks"
	{

		ip.setValue(255.0);							//This draws lines and numbers into image

		ip.moveTo(xx-nnl+bx,tt-mmb+bt);	//Kasten um Sparks zeichnen start links oben
		ip.lineTo(xx-nnl+bx,tt-mmb+at);		//links unten
		ip.lineTo(xx-nnl+ax,tt-mmb+at);		//rechts unten
		ip.lineTo(xx-nnl+ax, tt-mmb+bt);	//rechts oben
		ip.lineTo(xx-nnl+bx,tt-mmb+bt);		//links oben


		int stringWidth = ip.getStringWidth(String.valueOf(ii));	//width of spark number
		int shiftNumberX = 0;
		int shiftNumberT = 0;

		if((xx-nnl+ax-0+stringWidth)>width)			//if spark number exceeds the image width (i.e. is on the right edge of the image)
		{
			shiftNumberX = (xx-nnl+ax-0+stringWidth)-width;	//shift the number to the left
		}

		if((tt-mmb+bt+2)<12)
		{					//if spark number is on the top edge of the image
			shiftNumberT = 12-(tt-mmb+bt+2);	//shift the number down
		}


		ip.moveTo(xx-nnl+ax-0-shiftNumberX, tt-mmb+bt+2+shiftNumberT);		//Set cursor to numbering position
		shiftNumberX = 0;					//reset shiftNumber
		ip.drawString(String.valueOf(ii));			//label now
	}
*/
}
	}	//This is the end of the loop for each interval
// IJ.write("ssks:"+tava[8][99999999]);//This produces an error to keep the intermediate output values
}

//IJ.showMessage("done");


		// abb was this
		//float finalTava[][] = new float[17][500];		//This is the array that holds the final output values
		//int abbMaxLCR = 10000;
		float finalTava[][] = new float[17][abbMaxLCR];		//This is the array that holds the final output values
							//These values are used for the output in the table and for the boxes around sparks in the image
		int finalSkc = 1;								//final sparks counter

		for (int k =1; k <skc+1; k++)
		{
			if(tava[0][k] != 0)				//if amplitde was not set to 0 because of repeated spark
			{								//copy the values into the array which holds the final results
				finalTava[0][finalSkc] = tava[0][k];
				finalTava[1][finalSkc] = tava[1][k];
				finalTava[2][finalSkc] = tava[2][k];
				finalTava[3][finalSkc] = tava[3][k];
				finalTava[4][finalSkc] = tava[4][k];
				finalTava[5][finalSkc] = tava[5][k];
				finalTava[6][finalSkc] = tava[6][k];
				finalTava[7][finalSkc] = tava[7][k];
				finalTava[8][finalSkc] = tava[8][k];
				finalTava[9][finalSkc] = tava[9][k];
				finalTava[10][finalSkc] = tava[10][k];
				finalTava[11][finalSkc] = tava[11][k];
				finalTava[12][finalSkc] = tava[12][k];
				finalTava[13][finalSkc] = finalSkc;		//spark number
				finalTava[14][finalSkc] = tava[14][k];
				finalTava[15][finalSkc] = tava[15][k];
				finalTava[16][finalSkc] = tava[16][k];
				finalSkc = finalSkc + 1;			//count final spark counter 1 up
			}
		}

	if(imageBit==0)	ip.setValue(255.0);					//This defines the color of the line: highest color for each case: 255 for 8-bit and 65535 for 16-bit
		else ip.setValue(65535.0);

if((choiceoutputImg == 1)|(choiceoutputImg == 3)|(choiceoutputImg == 5))		//if outputImage should be "... + Sparks"
	{

	// abb this draws the roi ???
	System.out.println("abb drawing ROIs???");

	//System.out.println("neu["+n+"]= a["+i+"]= "+a[i]);

	for(int q=1; q<finalSkc+0; q++)
		{
			//ip.setValue(255.0);					//This draws lines and numbers into image

			//System.out.println("abb q:" + q + " finalTava[7][q]:" + (int)finalTava[7][q] + "(int)finalTava[9][q]:" + (int)finalTava[9][q]);

			int xTopLeft = (int)finalTava[7][q] + (int)finalTava[9][q];
			int yTopLeft = (int)finalTava[8][q] + (int)finalTava[11][q];

			int xBottomLeft = (int)finalTava[7][q] + (int)finalTava[9][q];
			int yBottomLeft = (int)finalTava[8][q] + (int)finalTava[12][q];

			int xBottomRight = (int)finalTava[7][q] + (int)finalTava[10][q];
			int yBottomRight = (int)finalTava[8][q] + (int)finalTava[12][q];

			int xTopRight = (int)finalTava[7][q] + (int)finalTava[10][q];
			int yTopRight = (int)finalTava[8][q] + (int)finalTava[11][q];

			int myLeft = xTopLeft;
			int myTop = yTopLeft;
			int myRight = xBottomRight;
			int myBottom = yBottomLeft;

			System.out.println("abb ROI:" + q + " left:" + myLeft + " top:" + myTop + " right:" + myRight + " bottom:" + myBottom);

			ip.moveTo((int)finalTava[7][q] + (int)finalTava[9][q]  , (int)finalTava[8][q] + (int)finalTava[11][q]);	//Kasten um Sparks zeichnen start links oben
																													//Draw the box around Sparks at the top left
			ip.lineTo((int)finalTava[7][q] + (int)finalTava[9][q]  , (int)finalTava[8][q] + (int)finalTava[12][q]);	//links unten
																													//bottom left
			ip.lineTo((int)finalTava[7][q] + (int)finalTava[10][q] , (int)finalTava[8][q] + (int)finalTava[12][q]);	//rechts unten
																													//bottom right
			ip.lineTo((int)finalTava[7][q] + (int)finalTava[10][q] , (int)finalTava[8][q] + (int)finalTava[11][q]);	//rechts oben
																													//top right
			ip.lineTo((int)finalTava[7][q] + (int)finalTava[9][q]  , (int)finalTava[8][q] + (int)finalTava[11][q]);	//links oben
																													//top left

			int stringWidth = ip.getStringWidth(String.valueOf(q));	//width of spark number
			int shiftNumberX = 0;
			int shiftNumberT = 0;

			if(((int)finalTava[7][q]+(int)finalTava[10][q]+stringWidth)>width)			//if spark number exceeds the image width (i.e. is on the right edge of the image)
			{
				shiftNumberX = ((int)finalTava[7][q]+(int)finalTava[10][q]+stringWidth)-width;	//shift the number to the left
			}

			if(( (int)finalTava[8][q] + (int)finalTava[11][q]+2) <12)				//if spark number is on the top edge of the image
			{
				shiftNumberT = 12-((int)finalTava[8][q]+(int)finalTava[11][q]);		//shift the number down
			}

			ip.moveTo((int)finalTava[7][q]+(int)finalTava[10][q]-shiftNumberX, (int)finalTava[8][q]+(int)finalTava[11][q]+shiftNumberT);		//Set cursor to numbering position
			shiftNumberX = 0;					//reset shiftNumber
			// abb was this draws lcr # I am removing
			//ip.drawString(String.valueOf(q));			//write the number of spark into the image
		}
	}


	int outputCycles = finalSkc-0;		//number of output cycles for results table
	int labelLength = finalSkc-0;		//set length of label array
	if (finalSkc<13)			//if final number of sparks less than number of labels then labelLength = 12 and no of outputCycles =12
	{
		labelLength = 13;
		outputCycles = 13;
	}

	String[][] label = new String[2][labelLength];		//labels for final resultstable
	label[1][1]="Filename";
	label[1][2]="Sparks/100\u00B5m/sec";
	label[1][3]="Sparks in this Image";
	label[1][4]="\u00B5m*sec analyzed";
	label[1][5]="";
	label[1][6]="Scanning Speed (lps)";
	label[1][7]="Pixelsize (\u00B5m)";
	label[1][8]="Background";
	label[1][9]="Criteria";
	//label[1][9]="Criteria 2";
	label[1][10]="No of Intervals";
	label[1][11]="";					//"Initial Filter";
	label[1][12]="Scaling Factor";

	label[0][1] = title;
	label[0][2] = IJ.d2s((finalSkc-1)/(height*tscan/1000*(pr-0-(pl+0))*psize)*100,2);		//spark frequency
	label[0][3] = IJ.d2s(finalSkc-1,0);					//final number of sparks
	label[0][4] = IJ.d2s(height*tscan/1000*(pr-0-(pl+0))*psize);			//size of analyzed part of image in um*sec (excludes non-cellular background)
	label[0][5] = "";
	label[0][6] = IJ.d2s(1/tscan*1000,2);	//lps
	label[0][7] = IJ.d2s(psize,3);		//pixelsize
	label[0][8] = IJ.d2s(black,0);		//Background
	label[0][9] = IJ.d2s(cri,1);		//criteria
	label[0][10] = IJ.d2s(nin,0);		//no of intervals
	label[0][11] = "";			//;chooseFilter[choicechooseFilter];
	label[0][12] = IJ.d2s(factorForOutput,0);

	if(checkboxChoice[2]==false){		//Clears results window and therefore the intermediate results.  Do this only when single images are analyzed
		IJ.setColumnHeadings(headings);		//clear results window by writing the headings once again			################
	}


	for (int k=1; k<outputCycles; k++)
	{
			String sparkNo = IJ.d2s(finalTava[13][k],0);			//Final spark parameter output
			String amplitude = IJ.d2s(finalTava[0][k],3);
			String halfWidth = IJ.d2s(finalTava[1][k],2);
			String halfDur = IJ.d2s(finalTava[2][k],2);
			String xPos = IJ.d2s(finalTava[3][k],2);
			String yPos = IJ.d2s((finalTava[4][k]/1000),3);
			String fullDur = IJ.d2s(finalTava[5][k],2);
			String fullWidth = IJ.d2s(finalTava[6][k],2);
			String TtP = IJ.d2s(finalTava[14][k],2);
			String Tau = IJ.d2s(finalTava[15][k],2);
			String FF0max = IJ.d2s(finalTava[16][k],2);

			if(finalTava[14][k]==0) {		//if Time-to-Peak is 0 then empty output for TtP and FF0max
				TtP="";
				FF0max = "";
			}

			if(label[0][k]==null)			//if there are more sparks than parameters (i.e. label = null) , then fill in ""
			{
				label[0][k]="";
				label[1][k]="";
			}

			if(k>finalSkc-1)			//if there are more parameters than sparks, then fill sparks output parameters with ""
			{
				sparkNo = "";
				amplitude = "";
				halfWidth = "";
				halfDur = "";
				xPos = "";
				yPos = "";
				fullDur = "";
				fullWidth = "";
				TtP = "";
				Tau = "";
				FF0max = "";
			}

			if (checkboxChoice[1]==true)		//Output of final results
				IJ.write(sparkNo+"	 "+amplitude+ "	"+halfWidth+"	"+halfDur+"	"+fullWidth+"	"+fullDur+"	"+TtP+"	"+FF0max+"	"+Tau+"	"+xPos+"	"+yPos+"	"+label[0][k]+"	"+label[1][k]);
			else
				IJ.write(sparkNo+"	 "+amplitude+ "	"+halfWidth+"	"+halfDur+"	"+xPos+"	"+yPos+"	"+label[0][k]+"	"+label[1][k]);

	}
			//maybe add a statusbar message
			if (checkboxChoice[2]==true){		//if all open images are analyzed insert two blank lines after analysis table
				IJ.showProgress((double)(imageNo+1)/noOfImages);
				IJ.write("");
				IJ.write("");
			}
			//check imageJ version
			//change default message
			if(imageNo==noOfImages) IJ.showProgress((double)2);
			activeImage.updateAndDraw();
	}	//This is the end of the Program

	IJ.log("Saving results:" + csvPath);
	//IJ.saveAs("Results", "/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210115/Results.csv");
	IJ.saveAs("Results", csvPath);

// this is saving the tif???
//IJ.save("/Users/cudmore/Desktop/tmp");
// above, we are using "IJ.write" to append to the table
// where the fuck is this in the ImageJ documentation???

} // run		//This is the end of the cycle through the open images
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	void showAbout()
	{
		IJ.showMessage("About SparkMaster_...",
			"SparkMaster (c)2006 by E. Picht");
	}

	public static int min(int a[]){
		//Equivalent der IDL 'min' Funktion
		//Gibt den kleinsten Wert des Eingabearrays int a[] aus

		int min = 700000;		//Mit hohem Wert starten, der in der folg. Schleife auf den kleinsten Wert gesetzt wird

		for (int i=0; i<a.length; i++){
			if (a[i]<min){
				min = a[i];
			}
		}

		return (int) min;
	}

	public static int max(int a[]){
		//Equivalent der IDL 'max' Funktion
		//Gibt den groessten Wert des Eingabearrays int a[] aus

		int min = -700000;		//Mit kleinem Wert starten, der in der folg. Schleife auf den groessten Wert gesetzt wird

		for (int i=0; i<a.length; i++){
			if (a[i]>min){
				min = a[i];
			}
		}

		return (int) min;
	}

	public static float max(float a[]){
		//Equivalent der IDL 'max' Funktion
		//Gibt den groessten Wert des Eingabearrays float a[] aus
		//DIES IST DIE FLOAT VERSION

		float min = -700000;		//Mit kleinem Wert starten, der in der folg. Schleife auf den groessten Wert gesetzt wird

		for (int i=0; i<a.length; i++){
			if (a[i]>min){
				min = a[i];
			}
		}

		return (float) min;
	}

	public static float min(float a[]){
		//Equivalent der IDL 'max' Funktion
		//Gibt den groessten Wert des Eingabearrays float a[] aus
		//DIES IST DIE FLOAT VERSION

		float min = 700000;		//Mit hohemem Wert starten, der in der folg. Schleife auf den kleinsten Wert gesetzt wird

		for (int i=0; i<a.length; i++){
			if (a[i]<min){
				min = a[i];
			}
		}

		return (float) min;
	}


	public static float min(double a[]){
		//Equivalent der IDL 'max' Funktion
		//Gibt den groessten Wert des Eingabearrays float a[] aus
		//DIES IST DIE FLOAT VERSION

		double min = 700000;		//Mit hohemem Wert starten, der in der folg. Schleife auf den kleinsten Wert gesetzt wird

		for (int i=0; i<a.length; i++){
			if (a[i]<min){
				min = a[i];
			}
		}

		return (float) min;
	}

	public static float max(double a[]){
		//Equivalent der IDL 'max' Funktion
		//Gibt den groessten Wert des Eingabearrays int a[] aus
		//DIES IST DIE FLOAT VERSION

		double min = -700000;		//Mit kleinem Wert starten, der in der folg. Schleife auf den groessten Wert gesetzt wird

		for (int i=0; i<a.length; i++){
			if (a[i]>min){
				min = a[i];
			}
		}

		return (float) min;
	}



	public static int whereZaehler(float a[], String comp, float value){
		//Equivalent zur IDL 'where' Funktion
		//GIBT NUR DIE GROESSE DES AUSGABEAARYS AUS!!!
		//float a[]		Eingabearray
		//String comp	entweder: eq (==), ne (!=), ge(>)
		//float value	Vergleichswert
		//Werte des Ausgabearrays sind die POSITIONEN im Eingabearray,
		//deren Werte einen wahren Vergleich liefern

		int zaehler=0;
		int zwischen[] = new int[a.length];	//in diesem temporaeren Array werden die Positionen mit wahrem Vergleich abgelegt

		if (comp=="ne"){			//not equal
			for (int i=0; i<a.length; i++){
						if (a[i] != value){
							zwischen[zaehler] = i;
							zaehler = zaehler + 1;
						}
			}
		}

		if (comp=="eq"){			//equal
			for (int i=0; i<a.length; i++){
						if (a[i] == value){
							zwischen[zaehler] = i;
							zaehler = zaehler + 1;
						}
			}
		}

		if (comp=="ge"){			//greater
			for (int i=0; i<a.length; i++){
						if (a[i] > value){
							zwischen[zaehler] = i;
							zaehler = zaehler + 1;
						}
			}
		}

//		int ausgabe[] = new int[zaehler];	//Ausgabearray der entsprechenden Groesse anlegen
//		for (int i=0; i<zaehler; i++){
//			ausgabe[i] = zwischen[i];		//Werte des zu grossen zwischen-Arrays ins Ausgabearray kopieren
//		}

		return (int) zaehler;	//Gibt die Groesse des Ausgebearrays aus
	}

	public static int[] where(float a[], String comp, float value){
		//Equivalent zur IDL 'where' Funktion
		//float a[]		Eingabearray
		//String comp	entweder: eq (==), ne (!=), ge(>)
		//float value	Vergleichswert
		//Werte des Ausgabearrays sind die POSITIONEN im Eingabearray,
		//deren Werte einen wahren Vergleich liefern

		int zaehler=0;
		int zwischen[] = new int[a.length];	//in diesem temporaeren Array werden die Positionen mit wahrem Vergleich abgelegt

		if (comp=="ne"){			//not equal
			for (int i=0; i<a.length; i++){
						if (a[i] != value){
							zwischen[zaehler] = i;
							zaehler = zaehler + 1;
						}
			}
		}

		if (comp=="eq"){			//equal
			for (int i=0; i<a.length; i++){
						if (a[i] == value){
							zwischen[zaehler] = i;
							zaehler = zaehler + 1;
						}
			}
		}

		if (comp=="ge"){			//greater
			for (int i=0; i<a.length; i++){
						if (a[i] > value){
							zwischen[zaehler] = i;
							zaehler = zaehler + 1;
						}
			}
		}

		int ausgabe[] = new int[zaehler];	//Ausgabearray der entsprechenden Groesse anlegen
		for (int i=0; i<zaehler; i++){
			ausgabe[i] = zwischen[i];		//Werte des zu grossen zwischen-Arrays ins Ausgabearray kopieren
		}

		return (int[]) ausgabe;	//Gibt das Ausgebearrays aus
	}







public static int[] transform(int a[], int aHeight, int aWidth, int zHeight, int zWidth){
		//Kopiert das kleine Eingabearray a[] mit den Dimensionen aHeight und aWidth
		//in das groessere Ausgabearray mit den Dimensionen zHeight und zWidth

		int z[] = new int[zHeight*zWidth];

		for(int i=0; i<z.length; i++){
			z[i]=1;
		}

		int iOffset, jOffset, i, j;

		for (int y=0; y<aHeight; y++){
			iOffset = y*aWidth;
			jOffset = y*zWidth;
			for (int x=0; x<aWidth; x++){
				i = iOffset + x;
				j = jOffset + x;
				z[j] = a[i];
			}
		}
		return (int[]) z;
	}

public static float[] transform(float a[], int aHeight, int aWidth, int zHeight, int zWidth){
		//Kopiert das kleine Eingabearray a[] mit den Dimensionen aHeight und aWidth
		//in die linke obere Ecke des groesseren Ausgabearrays z[] mit den Dimensionen zHeight und zWidth
		//IST NUR FUER DIE KONTROLLAUSGABE IN IMAGEJ GEDACHT
		//DIES IST DIE VERSION FUER FLOAT

		float z[] = new float[zHeight*zWidth];

		for(int i=0; i<z.length; i++){		//Ausgabearray mit Einsen fuellen
			z[i]=1;
		}

		int iOffset, jOffset, i, j;

		for (int y=0; y<aHeight; y++){
			iOffset = y*aWidth;
			jOffset = y*zWidth;
			for (int x=0; x<aWidth; x++){
				i = iOffset + x;
				j = jOffset + x;
				z[j] = a[i];
			}
		}

		return (float[]) z;
	}


public static int[] arrayPaste(int a[], int aHeight, int aWidth, int z[], int zHeight, int zWidth, int zTop, int zLeft){
		//Kopiert das kleine Eingabearray a[] mit den Dimensionen aHeight und aWidth
		//an die durch zTop und zLeft gegebene Pos des groesseren Ausgabearrays z[] mit den Dimensionen zHeight und zWidth

		int iOffset, jOffset, i, j;

		for (int y=0; y<aHeight; y++){
			iOffset = y*aWidth;
			jOffset = (y+zTop)*zWidth;
			for (int x=0; x<aWidth; x++){
				i = iOffset + x;
				j = jOffset + zLeft + x;
				z[j] = a[i];
			}
		}

		return (int[]) z;
	}



	public static int[] arrayCopy(int a[], int height, int width, int leftEdge, int rightEdge, int topEdge, int bottomEdge){
		//Kopiert einen durch die Parameter leftEdge, rightEdge, topEdge und bottomEdge definierten
		//Bereich des Eingabearrays float a[] in das Ausgabearray.
		//Die Dimensionen des Ausgabearrays werden durch die Parameter bestimmt.
		// int height, int width, Hoehe und Weite des Eingabearrays

		int newHeight = bottomEdge - topEdge + 1 ;	//Hoehe des Ausgabearrays
		int newWidth = rightEdge - leftEdge + 1;	//Weite des Ausgabearrays

		//System.out.println("newHeight = "+bottomEdge+" - " + topEdge+" = "+newHeight);
		//System.out.println("newWidth = "+rightEdge+" - " + leftEdge+" = "+newWidth);

		int neu[] = new int[newHeight*newWidth];	//Ausgabearray anlegen

		//System.out.println("neu.length= "+neu.length);

		int n = 0;	//Index des Ausgabearrays

		for (int y=(topEdge); y<(bottomEdge+1); y++){
			int offset, i;
			offset = y*width;
			for (int x=(leftEdge); x<(rightEdge+1); x++){
				i = offset +x;
				//System.out.println("neu["+n+"]= a["+i+"]= "+a[i]);
				neu[n] = a[i];
				n = n + 1;
				}
			}
		return (int[]) neu;
	}

	public static float[] arrayCopy(float a[], int height, int width, int leftEdge, int rightEdge, int topEdge, int bottomEdge){
		//Kopiert einen durch die Parameter leftEdge, rightedge, topEdge und bottomEdge definierten
		//Bereich des Eingabearrays float a[] in das Ausgabearay.
		//Die Dimensionen des Ausgabearrays werden durch die Parameter bestimmt.
		// int height, int width, Hoehe und Weite des Eingabearrays
		// DIES IST DIE VERSION FUER FLOAT ARRAYS

		int newHeight = bottomEdge - topEdge + 1;	//Hoehe des Ausgabearrays
		int newWidth = rightEdge - leftEdge + 1;	//Weite des Ausgabearrays

		//System.out.println("newHeight = "+bottomEdge+" - " + topEdge+" = "+newHeight);
		//System.out.println("newWidth = "+rightEdge+" - " + leftEdge+" = "+newWidth);

		float neu[] = new float[newHeight*newWidth];	//Ausgabearray anlegen

		//System.out.println("neu.length= "+neu.length);

		int n = 0;	//Index des Ausgebearrays

		for (int y=(topEdge); y<(bottomEdge+1); y++){
			int offset, i;
			offset = y*width;
			for (int x=(leftEdge); x<(rightEdge+1); x++){
				i = offset +x;
				//System.out.println("neu["+n+"]= a["+i+"]= "+a[i]);
				neu[n] = a[i];
				n = n + 1;
				}
			}
		return (float[]) neu;
	}



	public static int total(int[]a){
		//Gibt die Summe die Summe aller Elemente des Eengabearrays aus

		int zaehler=0;

		for(int i=0; i<a.length; i++){
			zaehler = zaehler + a[i];
		}
		return (int)zaehler;
	}

	public static float total(float[]a){
		//Gibt die Summe die Summe aller Elemente des Eengabearrays aus

		float zaehler = 0;

		for(int i=0; i<a.length; i++){
			zaehler = zaehler + a[i];
		}
		return (float)zaehler;
	}

	public static float total(double[]a){
		//Gibt die Summe die Summe aller Elemente des Eengabearrays aus

		double zaehler = 0;

		for(int i=0; i<a.length; i++){
			zaehler = zaehler + a[i];
		}
		return (float)zaehler;
	}

	public static float total(byte[]a){
		//Gibt die Summe die Summe aller Elemente des Eengabearrays aus

		double zaehler = 0;

		for(int i=0; i<a.length; i++){
			zaehler = zaehler + a[i];
		}
		return (float)zaehler;
	}


	public static int[] edgeCare(int a[], int height, int width, int ss, int st){
		//Fuellt die Raender des Eingabearrays int a[] mit Nullen


		for (int y=0; y<height; y++){
			int offset, i;
			offset = y*width;
			for (int x=0; x<(ss); x++){				//linke Reihen
				i = offset +x;
				a[i] = 0;
			}

			for (int x=(width-ss); x<(width); x++){		//rechte Reihen
				i = offset +x;
				a[i] = 0;
			}
		}

		for (int y=0; y<(st); y++){					//obere Reihen
			int offset, i;
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = 0;
			}
		}

		for (int y=(height-st); y<(height); y++){					//untere Reihen
			int offset, i;
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = 0;
			}
		}


		return (int[]) a;
	}

	public static float[] edgeCare(float a[], int height, int width, int ss, int st){
		//Fuellt die Raender des Eingabearrays float a[] mit Nullen
		//Float Version

		for (int y=0; y<height; y++){
			int offset, i;
			offset = y*width;
			for (int x=0; x<(ss); x++){				//linke Reihen
				i = offset +x;
				a[i] = 0;
			}

			for (int x=(width-ss); x<(width); x++){		//rechte Reihen
				i = offset +x;
				a[i] = 0;
			}
		}

		for (int y=0; y<(st); y++){					//obere Reihen
			int offset, i;
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = 0;
			}
		}

		for (int y=(height-st); y<(height); y++){					//untere Reihen
			int offset, i;
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = 0;
			}
		}


		return (float[]) a;
	}


	public static float[] edgeCare1(float a[], int height, int width, int left, int right, int top, int bottom){
		//Fuellt die Raender des Eingabearrays float a[] mit Einsen
		//float a[]	Eingabearray
		//height, width 	Dimensionen des Eingabearrays
		//int ss	No of columns to the left and right
		//int st	No of line on the top and bottom
		//Float Version

		for (int y=0; y<height; y++){
			int offset, i;
			offset = y*width;
			for (int x=0; x<(left); x++){				//linke Reihen
				i = offset +x;
				a[i] = 1;
			}

			for (int x=(width-right); x<(width); x++){		//rechte Reihen
				i = offset +x;
				a[i] = 1;
			}
		}

		for (int y=0; y<(top); y++){					//obere Reihen
			int offset, i;
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = 1;
			}
		}

		for (int y=(height-bottom); y<(height); y++){					//untere Reihen
			int offset, i;
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = 1;
			}
		}


		return (float[]) a;
	}



	public static float[] normalize(float a[], int height, int width, float denom[]){
		//Normalisiert a[] auf denom[] entlang der Zeitachse
		//width.a[] und length.denom[] muessen identisch sein

		//float b[] = new float[a.length];

		int offset, i;
		for (int y=0; y<height; y++){
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset +x;
				a[i] = a[i]/denom[x];
			}
		}
		return (float[]) a;
	}

	public static int edgeLeft(float a[], int black){
		//Gibt die linke Grenze fuer Pixel > black aus
		//float b[] = new float[a.length];
		int edge = 0;

		for (int i=(a.length-1); i>(-1); i--){
			if (a[i]>black){
				edge = i;		//die letzte Spalte, die groesser als Black ist
			}
		}
		return (int) edge;
	}

	public static int edgeRight(float a[], int black){
		//Gibt die rechte Grenze fuer Pixel > black aus
		//float b[] = new float[a.length];
		int edge = 0;

		for (int i=0; i<a.length; i++){
			if (a[i]>black){
				edge = i;		//die letzte Spalte, die groesser als Black ist
			}
		}
		return (int) edge;
	}

	public static float[] rebin1D(float a[], int height, int width){
		//Berechnet den Mittelwert jeder Spalte des Eingabearays a[]
		//und gibt ein neues 1D Aray mit den Mittelwerten aus

		//Eingabewerte:
		//	float a[]		Array, aus dem die Mittelwerte berechnet werden
		//		int height	Lange von a[]
		//		int width	Weite von a[]
		float b[] = new float[width];
		float sum = 0;	//Summenwert einer Spalte

//		int offset, i;
		int i;
		for (int y=0; y<width; y++){
//			offset = y*height;
			for (int x=0; x<height; x++){
				i = y +(x*width);
				sum = sum + a[i];
				//System.out.println("["+i+"] = "+a[i]);
			}
			//System.out.println("Sum= "+sum);
			b[y] = sum/height;
			//IJ.showMessage("Mittel= "+b[y]+"\r");
			sum =0;
		}
		return (float[]) b;
	}

	public static float[] rebinZeile(float a[], int height, int width){
		//Berechnet den Mittelwert jeder ZEILE des Eingabearays a[]
		//und gibt ein neues 1D Aray mit den Mittelwerten aus

		//Eingabewerte:
		//	float a[]		Array, aus dem die Mittelwerte berechnet werden
		//		int height	Lange von a[]
		//		int width	Weite von a[]
		float b[] = new float[height];
		float sum = 0;	//Summenwert einer Spalte

		int offset, i;
		for (int y=0; y<height; y++){
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset + x;
				sum = sum + a[i];
				//System.out.println("["+i+"] = "+a[i]);
			}
			//System.out.println("Sum= "+sum);
			b[y] = sum/width;
			//IJ.showMessage("Mittel= "+b[y]+"\r");
			sum =0;
		}
		return (float[]) b;
	}



	public static float[] spatioTemporal(int a[], int height, int width, int ss, int st){
		//Spezieller smoothing Filter:
		//Bewegt a[] von ss/2 nach links bis ss/2 nach rechts, summiert und berechnet den Mittelwert

		//Eingabewerte:
		//	int a[]			Array, auf das der Filter angewandt wird
		//		int height	Laenge des Arrays
		//		int width	Weite des Arrays
		// int ss			shift entlang der Scanachse
		// int st			shift entlang der Zeitachse

		float imb[] = new float[a.length];		//Int[] fuer Summierung
		int s = (int)ss/2;
		int t = (int)st/2;
		int ct = (2*s + 1) + (2*t +1);			//Counter, durch den spaeter geteilt wird
		int ii = 0;			//Index zum lesen des Originalarrays


		//System.out.println("s = "+s+" t = "+t);

		//Shift in horizontaler Richtung
		int offset, i;
		for (int y=0; y<height; y++){
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset + x;

				//System.out.println("line= "+y+" col= "+x);

				for(int xs=-s; xs<s+1; xs++){
					ii = x + xs;
						if(ii < 0){			//Ist der Fall fuer die ersten Pixel, wenn ans Ende der Zeile gesprungen werden muss
							ii = (width + 0) + ii;
						}

						if(ii > (width-1)){		//Ist der Fal fuer die letzen Pixel, wenn an den Beginn der Zeile gesprungen werden muss
							ii = ii - (width + 0);
						}
					//System.out.println("Offset + ii: "+offset+" + "+ii+"= "+(offset+ii));
					//System.out.println("");
					imb[i] = imb[i] + a[offset + ii];
				}
			}
		}

		//Shift in vertikaler Richtung
		offset=0;
		i=0;
		for (int y=0; y<height; y++){
			offset = y*width;
			for (int x=0; x<width; x++){
				i = offset + x;
				//System.out.println("");
				//System.out.println("line= "+y+" col= "+x);
				//System.out.println("Pixel= "+i);
				for(int xt=-t; xt<t+1; xt++){
					ii = xt * (width);
						if(i + ii < 0){			//Ist der Fall fuer die ersten Pixel, wenn ans Ende der Zeile gesprungen werden muss
							ii = (height * width) + ii;
						}

						if((i + ii) > (height * width - 1)){		//Ist der Fal fuer die letzen Pixel, wenn an den Beginn der Zeile gesprungen werden muss
							ii = ii - (height * width);
						}
					//System.out.println("Offset + ii: "+offset+" + "+ii+"= "+(i+ii));

					imb[i] = imb[i] + a[(i+ ii)];
				}
			}
		}

		//imb[] durch ct dividieren
		float imbf[] = new float[a.length];	//Float[] fuer Ausgabe nach Division
		for (int b=0; b<imb.length; b++){
			imbf[b]=(float)imb[b]/(float)ct;
			//System.out.println(imbf[b]);
		}
		//System.out.println("counter: "+ct);
		return (float[]) imbf;
	}

	public static float[] cutoff(float a[], float mittel, float cri, float stAbw){
		//Berechnet Mittelwert und Standardabweichung des Eingabearrays a[]
		//und legt ein neues int Array der gleichen Groesse an, in dem Pixel,
		//die > mittel + cri*stAb sind auf 1 gesetzt werden
		//Eingabewerte:
		//	int a[]			Array, dessen Werte ueberprueft werden
		//	float cri		Kriterium, Faktor mal Standarsabweichung

		float maske[] = new float[a.length];	//Maskenarray der gleichen Groesse anlegen
		//String stringNumber;
		//int intNumber;

		for (int i=0; i<a.length; i++){
			if(a[i]>(mittel + cri*stAbw)){
				maske[i] = 1;}

			if(a[i]>=0){			//Wenn a[i] = NaN, dann Maske[i] = 1
			// leere Anweisung
			}
			else{
			maske[i] = 1;}

		}
		//IJ.showMessage("Threshold: "+(mittel+cri*stAbw));
		//IJ.showMessage("a[3]: "+a[3]);

		//IJ.showMessage("maske[3]: "+maske[3]);
		return (float[]) maske;
	}

	public static float[] medianFilter(float a[], int height, int width, int xKernel, int tKernel){

		//Median Filter fuer int Array
		//Eingabewerte:
		//	int a[]			Array, auf das der Filter angewandt wird
		//		int height	Laenge des Arrays
		//		int width	Weite des Arrays
		//	int xKernel		Weite des Filter Kernels
		//	int tKernel			Laenge des Filter Kernels in t-Richtung
		//Die nicht gefilterten Raender enthalten die original Werte
//IJ.write("medianFilter");
		float b[] = new float[height*width];		//Array b[] in der gleichen Groesse anlegen
		b = (float[]) a.clone();					//Original Array ins spaetere Ausgabearray kopieren (fuer Raender)

		float ein[] = new float[xKernel*tKernel];	//Originalwerte werden zur Berechnung hier eingelesen
//		int einZaehler = xKernel * tKernel;

		int offset;//, i;
		int offsetEin;
		for (int y=0; y<(height+1-tKernel); y++){	//Raender
			offset = y*width;
			for (int x=0; x<(width+1-xKernel); x++){

				for (int d1=0; d1<tKernel; d1++){
					offsetEin = d1*xKernel;
					for (int d2=0; d2<xKernel; d2++){
					//	System.out.println("offset+x: "+(offset + x)+" offsetEin+d2: "+((tKernel/2)+(xKernel/2)*width+(offset+x)));
					//	System.out.println("offset: "+(offset+x+d2*width));
					//	System.out.println("#: "+(offset+x+d2+d1*width)); 	//Referenzen fuer Kernel
						ein[offsetEin + d2] = a[(offset+x+d2+d1*width)];	//Werte aus dem Originalarray (a) in das Kernelarray (ein) einlesen
					//	System.out.println("ein["+(offsetEin + d2)+"] = "+ein[offsetEin + d2]);
					}
				}

				b[(tKernel/2)*width+(xKernel/2)+(offset+x)] = median(ein);
				//System.out.println("Median: "+b[(tKernel/2)*width+(xKernel/2)+(offset+x)]);
				//System.out.println("");
			}
		}
		return (float[]) (b);
	}

	public static float[] smoothFilter(float a[], int height, int width, int xKernel, int tKernel){
		//System.out.println("smoothFilter started"+"\r");
		//Smooth Filter fuer int Array
		//Eingabewerte:
		//	int a[]			Array, auf das der Filter angewandt wird
		//		int height	Laenge des Arrays
		//		int width	Weite des Arrays
		//	int xKernel			Weite des Filter Kernels
		//	int tKernel			Laenge des Filter Kernels in t-Richtung
//IJ.write("smoothFilter");
		float b[] = new float[height*width];		//Array b[] in der gleichen Groesse anlegen
		b = (float[]) a.clone();	//kopieren (damit Originalwerte an den Raendern beibehalten werden)

///		float ein[] = new float[xKernel*tKernel];	//Originalwerte werden zur Berechnung hier eingelesen
float groesseKernel = xKernel * tKernel;
float ein =0;
///		int einZaehler = xKernel * tKernel;

		int offset;//, i;
//		int offsetEin;
		//System.out.println("smoothFilter height: "+height);
		//System.out.println("smoothFilter tKernel: "+tKernel+"\r");
		for (int y=0; y<(height+1-tKernel); y++){	//Raender
			offset = y*width;
			//System.out.println("smoothFilter inner loop");

			for (int x=0; x<(width+1-xKernel); x++){
				//System.out.println("smoothFilter width: "+width);
				//System.out.println("smoothFilter xKernel: "+xKernel);

				for (int d1=0; d1<tKernel; d1++){
					//System.out.println("inner inner loop");

//					offsetEin = d1*xKernel;
					for (int d2=0; d2<xKernel; d2++){
					//	System.out.println("offset+x: "+(offset + x)+" offsetEin+d2: "+((tKernel/2)+(xKernel/2)*width+(offset+x)));
					//	System.out.println("offset: "+(offset+x+d2*width));
					//	System.out.println("#: "+(offset+x+d2+d1*width)); 	//Referenzen fuer Kernel
///						ein[offsetEin + d2] = a[(offset+x+d2+d1*width)];	//Werte aus dem Originalarray (a) in das Kernelarray (ein) einlesen
ein = ein + a[(offset+x+d2+d1*width)];
						//System.out.println("ein["+(offsetEin + d2)+"] = "+ein[offsetEin + d2]);
					}
				}
				//System.out.println("mittel(ein): "+mittel(ein));
				//System.out.println(((tKernel/2)*width+(xKernel/2)+(offset+x)));
///				b[(tKernel/2)*width+(xKernel/2)+(offset+x)] = mittel(ein);
b[(tKernel/2)*width+(xKernel/2)+(offset+x)] = ein/groesseKernel;
ein =0;
				//System.out.println("Mittel: "+b[(tKernel/2)+(xKernel/2)*width+(offset+x)]);
				//System.out.println("");
			}
		}
		return (float[]) (b);
	}

	public static int median(float a[]){
		//Berechnung des Medians
		//Diese Routine ist adaptiert aus "Image processing in Java" pg. 203

		Arrays.sort(a);				//Benoetigt import java.util.*
		int mid = a.length/2-0;		//-1 weil Array bei [0] beginnt

		if((a.length & 1)==1)		//Wenn Anzahl der Elemente des Arrays ungerade
			return (int)a[mid];

		return (int)(((double)a[mid]+(double)a[mid-1])/2);
	}

	public static float mittel(float a[]){
		//Berechnet den Mittelwert eine Arrays vom Typ float
		//IJ.showMessage("Mittel");

		float summe=0;
		for (int i =0; i<a.length; i++)
			 summe = summe + a[i];

		return (float) (summe/(float)a.length);
	}

	public static float mittel(int a[]){
		//Berechnet den Mittelwert eines Arrays von Typ integer
		//IJ.showMessage("Mittel");

		float summe=0;
		for (int i =0; i<a.length; i++)
			 summe = summe + a[i];

		return (float) (summe/(float)a.length);
	}


	public static float stDevEdges(float a[], int height, int width, int leftEdge, int rightEdge){
		//Berechnet die StandardAbweichung = Wurzel der Varianz
		// 	float a[]		Eingabearray
		//	int height, width	Dimensionen des Eingabearrays
		//	int leftEdge, rightEdge	Bereich, aus dem die Standardabweichung berechnet werden soll



		float varianzSumme = 0;
		float varianz = 0;
		float stDev = 0;
		float summe = 0;
		float mittel = 0;

		//Berechnung des Mittelwertes
		int offset, i;
		for (int y=0; y < height; y++){
			offset = y*width;
			for (int x=leftEdge; x<(rightEdge+1); x++){
				i = offset + x;
				summe = summe + a[i];
			}
		}

		mittel = summe/(float)(height*(rightEdge+1-leftEdge));

		//Berechnung der Varianz
		offset = 0;
		i = 0;
		for (int y=0; y < height; y++){
			offset = y*width;
			for (int x=leftEdge; x<(rightEdge+1); x++){
				i = offset +x;
				varianzSumme = varianzSumme + (a[i]-mittel)*(a[i]-mittel);
			}
		}
		varianz = varianzSumme/(float)(height*(rightEdge+1-leftEdge)-1);
		//System.out.println("#Pixel: "+(height*(rightEdge-leftEdge)));
		stDev = (float)Math.sqrt(varianz);

		//System.out.println("Varianz: "+varianz);
		//System.out.println("StDev: "+stDev);
		//System.out.println(" ");

		return (float) stDev;
	}

	public static double stDev(float a[]){
		//Berechnet die StandardAbweichung = Wurzel der Varianz

		float varianzSumme = 0;
		float mittel = mittel(a); //Mittelwert des input Arrays
		double varianz = 0;
		double stDev;

		for (int i=0; i < a.length; i++)
			varianzSumme = varianzSumme + (a[i]-mittel)*(a[i]-mittel);

		varianz = varianzSumme/((double)(a.length-1));
		stDev = Math.sqrt(varianz);

		return (float) stDev;
	}


	public static float[] liveOrDie(float a[], int height, int width, int nSize, int nLive){

		//Density Filter fuer float Array
		//Eingabewerte:
		//	float a[]			Array, auf das der Filter angewandt wird
		//		int height	Laenge des Arrays
		//		int width	Weite des Arrays
		//  	int nSize		Groesse des Kernels
		//	int nLive		Anzahl von Pixeln in Kernel = 1
		//Die nicht gefilterten Raender enthalten die original Werte
//IJ.write("liveOrDie");
		float b[] = new float[height*width];		//Array b[] in der gleichen Groesse anlegen
		b = (float[]) a.clone();				//copy return array This is to keep the original values along the edges

		int xKernel = nSize;
		int tKernel = nSize;
///		int ein[] = new int[xKernel*tKernel];	//Originalwerte werden zur Berechnung hier eingelesen
///		int einZaehler = xKernel * tKernel;

//IJ.write("xKernel: "+xKernel+" nLive: "+nLive+" ");
		int offset;//, i;
//		int offsetEin;

		float summe = 0;		//Summiert die Werte aus Eingabearray wenn Kernel verschoben wird
		int d1=0;
		int d2=0;				//define counters d1 and d2 here
		int x = 0;

		for (int y=0; y<(height+1-tKernel); y++){	//Raender
			offset = y*width;
			//IJ.write("offset: "+offset+"  ");
			for (x=0; x<(width+1-xKernel); x++){

				for (d1=0; d1<tKernel; d1++){
//					offsetEin = d1*xKernel;
					for (d2=0; d2<xKernel; d2++){
					//	IJ.write("offset+x: "+(offset + x)+" offsetEin+d2: "+((tKernel/2)+(xKernel/2)*width+(offset+x)));
					//	IJ.write("offset: "+(offset+x+d2*width));
					//	IJ.write("#: "+(offset+x+d2+d1*width)+" = "+a[(offset+x+d2+d1*width)]+" "); 	//Referenzen fuer Kernel
					//	IJ.write("offset: "+offset+" x: "+x+" d1: "+d1+" d2: "+d2+" width: "+width+" ");

						summe = summe + a[(offset+x+d2+d1*width)];	//Werte aus dem Originalarray (a) in das Kernelarray (ein) einlesen

		//				ein[offsetEin + d2] = a[(offset+x+d2+d1*width)];	//Werte aus dem Originalarray (a) in das Kernelarray (ein) einlesen
//						IJ.write("ein["+(offsetEin + d2)+"] = "+ein[offsetEin + d2]);

					}
				}

			//IJ.write("Summe: "+summe+" ");
			if(summe>= nLive){				//If sum of kernel > nLive
				b[(tKernel/2)*width+(xKernel/2)+(offset+x)] = 1;
				}
			else{
				b[(tKernel/2)*width+(xKernel/2)+(offset+x)] = 0;
			}
			summe = 0;
			}


		}
		return (float[]) (b);
	}

	// read
	public static int[] lesen(int[]a)
	throws FileNotFoundException, IOException
	{
		// Reads the text from "c: /hugo.txt" and writes the values ​​into the
		//Liest den text aus "c:/hugo.txt" und schreibt die Werte in das
		//int[] ein

		int[] ein= new int[a.length];

		int zeile;
		//23532 // scan speed (lps) / 10
		//829 // pixelsize (um) 0.829 = 829 / 1000
		//25 // criterion = 2.5 = 25/10
		//20
		//1 // number of intervals
		//1
		//5
		//2 // background fiu
		//0
		//1 //Extended Kinetics
		//0
		FileReader in_file = new FileReader ("SpMValuesV100.txt");
		BufferedReader alt = new BufferedReader (in_file);

		//int i=0;

		for(int i=0; i<a.length; i++)
		{
			zeile = Integer.parseInt(alt.readLine());
			ein[i] = zeile;
		}
		alt.close();
		return (int[])ein;
	}

	// write
	public static int[] schreiben(int[]a)
	throws FileNotFoundException, IOException
	{
	//Does not give anything back but don't know how to declare that

	int[] ein= new int[a.length];
	int zeile;
	System.out.println("abb schreiben is write");
	System.out.println("Start schreiben");



		FileWriter out_file = new FileWriter ("SpMValuesV100.txt");
		BufferedWriter neu = new BufferedWriter (out_file);

		for (int j = 0;j<a.length;j++)
		{
			zeile = a[j];
			System.out.println("zeile: "+a[j]);
			neu.write(String.valueOf(zeile));
			System.out.println("j: "+j);
			neu.newLine();
		}
		neu.close();

		return (int[])ein;
	}

	public static float[] waveletFilter(float a[], int height, int width){
	//Performs the a trous wavelet transformation and denoising
	//Uses the algorithm available for download on the ImageJ website

	float stdev;
	double pix;
	double pix_d[] = new double[width*height];;	//this is the image
	double k1,k2,k3,k4, k5;    // thresholding coefficients

	k1=10;
	k2=5;
	k3=1;
	k4=0;
	k5=0;

	int m=50;
	double matrix_big[][]=new double[width+m*2][height+m*2];
	double matrix_big2[][]=new double[width+m*2][height+m*2];
	double matrix_big_s[][]=new double[width+m*2][height+m*2];
	double matrix_big2_s[][]=new double[width+m*2][height+m*2];
	double wave3d[][][]=new double[width+m*2][height+m*2][5];
	double wave3d_s[][][]=new double[width+m*2][height+m*2][5];
	byte pixels[]=new byte[width*height];

	for (int i=0;i<pix_d.length;i++){		//writes the input float[] image a[] into the double[] pix_d
		pix_d[i] = (double)a[i];
		pixels[i] = (byte)a[i];
	}
//IJ.showMessage("total(pixels): "+total(pixels)+"    ");


	stdev = noiseEstimate(a, height, width);
//	stdev=(float)7.969;
//IJ.showMessage("noiseEstimate stdev: "+stdev+"    ");

	// simulation of an image with mean=0 and std_dev=1
	ImagePlus simul = NewImage.createByteImage("Simulation",width,height,1,NewImage.FILL_BLACK);
	ImageProcessor simul_ip = simul.getProcessor();
	simul_ip.noise(1.67) ;//war 1.67
	byte[] pixels2 =(byte[])simul_ip.getPixels();

	double[] pix_s= new double[width*height];
	for(int i=0;i<pixels2.length;i++){
		pix = 0xff & pixels2[i];
		pix_s[i] = pix;				//pix_s[] is result of simulation
	}
//IJ.showMessage("total(pix_s): "+total(pix_s)+"    ");

	//initialisation of the simulated image
	for(int i=0;i<width+2*m;i++)
  		for(int j=0;j<height+2*m;j++)
    			matrix_big_s[i][j]=0;

	for(int i=0;i<width;i++)
		for(int j=0;j<height;j++)
			matrix_big_s[i+m][j+m]=pix_s[i+j*width];

	mirror(matrix_big_s,width,height,m);

	for(int i=0;i<width+2*m;i++)
  		for(int j=0;j<height+2*m;j++)
    			matrix_big2_s[i][j]=matrix_big_s[i][j];

	a_trous_transform(matrix_big_s, matrix_big2_s, wave3d_s, width, height, m);


	//initialisation of the image
	for(int i=0;i<width+2*m;i++)
  		for(int j=0;j<height+2*m;j++)
    			matrix_big[i][j]=0;

	for(int i=0;i<width;i++)
		for(int j=0;j<height;j++)
			matrix_big[i+m][j+m]=pix_d[i+j*width];

	mirror(matrix_big,width,height,m);

	for(int i=0;i<width+2*m;i++)
		for(int j=0;j<height+2*m;j++)
			matrix_big2[i][j]=matrix_big[i][j];


	a_trous_transform(matrix_big, matrix_big2, wave3d, width, height, m);

	denoise(wave3d, wave3d_s, width, height, m, stdev, k1, k2, k3, k4, k5);
//IJ.showMessage("total(pixels): "+total(pixels)+"    ");

	inverse(pix_d, pixels, matrix_big2, wave3d,width, height, m);
//IJ.showMessage("min(pix_d): "+min(pix_d)+"   max(pix_d): "+max(pix_d)+" ");
//IJ.showMessage("min(a): "+min(a)+"   max(a): "+max(a)+" ");

	for(int i = 0; i<pix_d.length; i++){
		a[i] = (float)pix_d[i];
	}
//IJ.showMessage("min(a): "+min(a)+"   max(a): "+max(a)+" ");

	return(float[]) a;
	}//waveletFilter


	public static float noiseEstimate(float a[], int height, int width){
	//The noise estimate is the standard deviation of the difference between the original and the 3x3 median filtered image

	float stDev=0;
	float difference[] = new float[height*width];	//Array for diference between input array and 3x3 median filtered input array

	float aMedian[] = new float[height*width];		//Array aMedian has same dimensions as input array
	aMedian = medianFilter(a, height, width,3,3);	//3x3 median filter on input array



	for(int i=0;i<width*height;i++){			//calculates the difference between the input aray and the filtered array
		difference[i]=a[i]-aMedian[i];
		if(difference[i]<0) difference[i]=0;
		if(difference[i]>255) difference[i]=255;
	}

	stDev = (float)stDev(difference);		//calculate the standard deviation of the difference array

	return(float) stDev;
	}//noiseEstimate






	public static void mirror(double[][] matrix_big, int width, int height, int m){


	//bottom
       	for(int i=0;i<width;i++){
              		for(int j=1;j<=m;j++){
                 			matrix_big[i+m][m-1+height+j]=matrix_big[i+m][m-1+height-j];
               		}
        	}

	//top
      	for(int i=0;i<width;i++){
        		for(int j=1;j<=m;j++){
          			matrix_big[i+m][m-j]=matrix_big[i+m][m+j];
                    	}
             	}


	//right
     	for(int i=0;i<=m;i++){
      		for(int j=0;j<height;j++){
			matrix_big[m-1+width+i][m+j]=matrix_big[m-1+width-i][m+j];
                   	}
           	}

	//left
     	for(int i=0;i<=m;i++){
      		for(int j=0;j<height;j++){
       			matrix_big[m-i][m+j]=matrix_big[m+i][m+j];
                   	}
         	}



	//top left corner
   	for(int i=0;i<=m;i++){
    		for(int j=0;j<=m;j++){
      			matrix_big[i][j]=matrix_big[2*m-i][2*m-j];
                 		}
       	}

	//bottom right corner
	for(int i=0;i<=m;i++){
   		for(int j=0;j<=m;j++){
     			matrix_big[i+width+m-1][j+height+m-1]=matrix_big[width+m-1-i][height+m-1-j];
                		}
      	}


	//top right corner
  	for(int i=0;i<=m;i++){
   		for(int j=0;j<=m;j++){
     			matrix_big[i+width+m-1][j]=matrix_big[m-1+width-i][m*2-j];
                		}
      	}

	//bottom left corner
	for(int i=0;i<=m;i++){
		for(int j=0;j<=m;j++){
			matrix_big[i][j+height+m-1]=matrix_big[2*m-i][height+m-1-j];
                		}
      	}

	}//mirror






	//perform the a trous wavelet transform
	public static void a_trous_transform( double[][] matrix_big, double[][] matrix_big2, double[][][] wave3d, int width, int height, int m){

 double matrix_tmp[][]=new double[width+m*2][height+m*2];
 double wave_t[][]=new double[width+m*2][height+m*2];
 int distance[]= {1,2,4,8,16,32,64};

    for(int i=0;i<width;i++)
      for(int j=0;j<height;j++)
        wave_t[i+m][j+m]=0;



    for(int k=0;k<5;k++){

 convolution(matrix_big, matrix_big2,  distance[k],  distance[k+1],  width,  height,  m);


  for(int i=0;i<width+m*2;i++)
    for(int j=0;j<height+m*2;j++)
      wave_t[i][j]=matrix_big[i][j]-matrix_big2[i][j];


  for(int i=0;i<width+m*2;i++)
    for(int j=0;j<height+m*2;j++)
      wave3d[i][j][k]=wave_t[i][j];


   for(int i=0;i<width+m*2;i++)
       for(int j=0;j<height+m*2;j++)
          matrix_tmp[i][j]=0;

      for(int i=m;i<width+m;i++)
       for(int j=m;j<height+m;j++)
          matrix_tmp[i][j]=matrix_big2[i][j];

   mirror(matrix_tmp,width,height,m);

   for(int i=0;i<width+m*2;i++)
       for(int j=0;j<height+m*2;j++)
          matrix_big2[i][j]=matrix_tmp[i][j];

      for(int i=0;i<width+m*2;i++)
       for(int j=0;j<height+m*2;j++)
          matrix_big[i][j]=matrix_big2[i][j];
  }

  }// a_trous






// convolution between the image and a 2D B3-spline function
public static void convolution(double[][] mat1, double[][]mat2, int p, int q, int width, int height, int m){

    for(int i=m;i<width+m;i++){
      for(int j=m;j<height+m;j++){

           mat2[i][j]=(mat1[i-q][j-q]/256 + mat1[i-q][j-p]/64 + mat1[i-q][j]*3/128 + mat1[i-q][j+1]/64 + mat1[i-q][j+q]/256 +
                mat1[i-p][j-q]/64 + mat1[i-p][j-p]/16 + mat1[i-p][j]*3/32 + mat1[i-p][j+p]/16 + mat1[i-p][j+q]/64 +
                mat1[i][j-q]*3/128 + mat1[i][j-p]*3/32 + mat1[i][j]*9/64 + mat1[i][j+p]/32 + mat1[i][j+q]*3/128 +
                mat1[i+p][j-q]/64 + mat1[i+p][j-p]/16 + mat1[i+p][j]*3/32 + mat1[i+p][j+p]/16 + mat1[i+p][j+q]/64 +
                mat1[i+q][j-q]/256 + mat1[i+q][j-p]/64 + mat1[i+q][j]*3/128 + mat1[i+q][j+p]/64 + mat1[i+p][j+q]/256);

       }
    }

  }//convolution




//remove the noise
public static void denoise(double[][][] wave, double[][][] wave_s, int width, int height,int m, double stddev, double k1, double k2, double k3, double k4, double k5){

   double[] dev_s= new double[5];

   stdev_calc_m(wave_s, dev_s, width, height, m);

 /*  for(int i=0;i<5;i++){
     result=IJ.d2s(dev_s[i]);
     IJ.write(result);
   }*/

    for(int i=0;i<width+m*2;i++){
     for(int j=0;j<height+m*2;j++){

        if( Math.abs(wave[i][j][0]) < k1*stddev*dev_s[0] ) wave[i][j][0]=0;
        if( Math.abs(wave[i][j][1]) < k2*stddev*dev_s[1] ) wave[i][j][1]=0;
        if( Math.abs(wave[i][j][2]) < k3*stddev*dev_s[2] ) wave[i][j][2]=0;
        if( Math.abs(wave[i][j][3]) < k4*stddev*dev_s[3] ) wave[i][j][3]=0;
        if( Math.abs(wave[i][j][4]) < k5*stddev*dev_s[4] ) wave[i][j][4]=0;

     }
     }

  }//denoise






//inverse transform
public static float[] inverse(double[] pix_d, byte[] pixels, double[][] matrix_big2, double[][][] wave3d, int width, int height, int m){
    float[]output=new float[width*height];
    double res[][]=new double[width+m*2][height+m*2];
    double res_petit[][]=new double[width][height];


 for(int i=0;i<width+m*2;i++)
    for(int j=0;j<height+m*2;j++)
       res[i][j]=matrix_big2[i][j]+wave3d[i][j][0]+wave3d[i][j][1]+wave3d[i][j][2]+wave3d[i][j][3]+wave3d[i][j][4];


           for(int i=0;i<width;i++){
             for(int j=0;j<height;j++){
               res_petit[i][j]=res[i+m][j+m];
              }
           }

           for(int i=0;i<width;i++){
             for(int j=0;j<height;j++){
               pix_d[i+j*(width)]=res_petit[i][j];
              }
           }

          for(int i=0;i<(width)*(height);i++){

             if (pix_d[i] < 0) pix_d[i]  = 0;
             if ( pix_d[i] > 255) pix_d[i]  = 255;

          }


           for(int i=0;i<width*height;i++)
               pixels[i]=(byte)pix_d[i];

	for(int i=0;i<width*height;i++){
		output[i]=(float)pixels[i];
	}

return (float[])output;
  }//inverse




// calculate the standard deviation of a matrix
  public static void stdev_calc_m(double[][][] tab, double[] res, int width, int height, int m){

    double mean_t=0;
    double sigma_t=0;
    double stdev_t=0;
    double size = width*height;

for(int k=0; k<5; k++){


    for(int i=m;i<width+m;i++)
      for(int j=m;j<height+m;j++)
          mean_t+=tab[i][j][k];
        //mean_t+=Math.abs(tab[i][j][k]);

      mean_t=mean_t/(size);

      for(int i=m;i<width+m;i++)
        for(int j=m;j<height+m;j++)
          sigma_t+=(tab[i][j][k]-mean_t)*(tab[i][j][k]-mean_t);

    sigma_t=sigma_t/(size);
    stdev_t=Math.sqrt(sigma_t);
    res[k]=stdev_t;

}
}//stdev_calc



}// abb plugin filter class
