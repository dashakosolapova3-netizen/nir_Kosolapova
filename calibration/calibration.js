var PointCalibrate = 0;
var CalibrationPoints={};

// Find the help modal
var helpModal;

/**
 * Clear the canvas and the calibration button.
 */
function ClearCanvas(){
  document.querySelectorAll('.Calibration').forEach((i) => {
    i.style.setProperty('display', 'none');
  });
  var canvas = document.getElementById("plotting_canvas");
  canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
}

/**
 * Show the instruction of using calibration at the start up screen.
 */
function PopUpInstruction(){
  ClearCanvas();
  swal({
    title:"Калибровка",
    text: "Пожалуйста, нажмите на каждую из 9 точек на экране. Нужно нажать на каждую точку 5 раз, пока она не станет жёлтой. Это откалибрует отслеживание взгляда.",
    buttons:{
      cancel: false,
      confirm: "Начать"
    }
  }).then(isConfirm => {
    ShowCalibrationPoint();
  });
}
/**
  * Show the help instructions right at the start.
  */
function helpModalShow() {
    if(!helpModal) {
        helpModal = new bootstrap.Modal(document.getElementById('helpModal'))
    }
    helpModal.show();
}

function calcAccuracy() {
    // show modal
    // notification for the measurement process
    swal({
        title: "Вычисление точности",
        text: "Пожалуйста, не двигайте мышь и смотрите на центральную точку в течение следующих 5 секунд. Это позволит измерить точность предсказаний.",
        closeOnEsc: false,
        allowOutsideClick: false,
        closeModal: true
    }).then( () => {
        // makes the variables true for 5 seconds & plots the points
    
        store_points_variable(); // start storing the prediction points
    
        sleep(5000).then(() => {
                stop_storing_points_variable(); // stop storing the prediction points
                var past50 = webgazer.getStoredPoints(); // retrieve the stored points
                var precision_measurement = calculatePrecision(past50);
                window.calibrationAccuracy = precision_measurement;
                updateAccuracyIndicator(precision_measurement);
                var accuracyLabel = `<a>Точность | ${precision_measurement}%</a>`;
                document.getElementById("Accuracy").innerHTML = accuracyLabel; // Show the accuracy in the nav bar.
                swal({
                    title: "Ваша точность: " + precision_measurement + "%",
                    allowOutsideClick: false,
                    buttons: {
                        cancel: "Повторить калибровку",
                        confirm: "ОК",
                    }
                }).then(isConfirm => {
                        if (isConfirm){
                            ClearCanvas();
                            // Показываем меню-контрол обратно
                            var controls = document.querySelector('.controls');
                            if (controls) controls.style.display = 'flex';
                            var offset = document.querySelector('.content-offset');
                            if (offset) offset.style.display = 'block';
                        } else {
                            document.getElementById("Accuracy").innerHTML = "<a>Не откалибровано</a>";
                            webgazer.clearData();
                            ClearCalibration();
                            ClearCanvas();
                            ShowCalibrationPoint();
                            // Меню-контрол НЕ показываем!
                        }
                });
        });
    });
}

function calPointClick(node) {
    const id = node.id;

    if (!CalibrationPoints[id]){ // initialises if not done
        CalibrationPoints[id]=0;
    }
    CalibrationPoints[id]++; // increments values

    if (CalibrationPoints[id]==5){ //only turn to yellow after 5 clicks
        node.style.setProperty('background-color', 'yellow');
        node.setAttribute('disabled', 'disabled');
        PointCalibrate++;
    }else if (CalibrationPoints[id]<5){
        //Gradually increase the opacity of calibration points when click to give some indication to user.
        var opacity = 0.2*CalibrationPoints[id]+0.2;
        node.style.setProperty('opacity', opacity);
    }

    //Show the middle calibration point after all other points have been clicked.
    if (PointCalibrate == 8){
        document.getElementById('Pt5').style.removeProperty('display');
    }

    if (PointCalibrate >= 9){ // last point is calibrated
        // grab every element in Calibration class and hide them except the middle point.
        document.querySelectorAll('.Calibration').forEach((i) => {
            i.style.setProperty('display', 'none');
        });
        document.getElementById('Pt5').style.removeProperty('display');

        // clears the canvas
        var canvas = document.getElementById("plotting_canvas");
        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);

        // Calculate the accuracy
        calcAccuracy();
    }
}

/**
 * Load this function when the index page starts.
* This function listens for button clicks on the html page
* checks that all buttons have been clicked 5 times each, and then goes on to measuring the precision
*/
//$(document).ready(function(){
function docLoad() {
  ClearCanvas();
  // helpModalShow(); // Убираем автоматический показ инструкции
    
    // click event on the calibration buttons
    document.querySelectorAll('.Calibration').forEach((i) => {
        i.addEventListener('click', () => {
            calPointClick(i);
        })
    })
};
document.addEventListener('DOMContentLoaded', docLoad);

/**
 * Show the Calibration Points
 */
function ShowCalibrationPoint() {
  document.querySelectorAll('.Calibration').forEach((i) => {
    i.style.removeProperty('display');
  });
  // initially hides the middle button
  document.getElementById('Pt5').style.setProperty('display', 'none');
}

/**
* This function clears the calibration buttons memory
*/
function ClearCalibration(){
  // Clear data from WebGazer

  document.querySelectorAll('.Calibration').forEach((i) => {
    i.style.setProperty('background-color', 'red');
    i.style.setProperty('opacity', '0.2');
    i.removeAttribute('disabled');
  });

  CalibrationPoints = {};
  PointCalibrate = 0;
}

// sleep function because java doesn't have one, sourced from http://stackoverflow.com/questions/951021/what-is-the-javascript-version-of-sleep
function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

function updateAccuracyIndicator(precision_measurement) {
    var indicator = document.getElementById('Accuracy');
    if (!indicator) return;
    if (precision_measurement === undefined || precision_measurement === null || isNaN(precision_measurement)) {
        indicator.innerHTML = '<a>Не откалибровано</a>';
        indicator.className = 'accuracy-indicator';
        indicator.title = 'Точность не измерена. Необходимо провести калибровку.';
        return;
    }
    indicator.innerHTML = `<a>Точность | ${precision_measurement}%</a>`;
    if (precision_measurement >= 80) {
        indicator.className = 'accuracy-indicator high';
        indicator.title = 'Высокая точность предсказания движения глаз';
    } else if (precision_measurement >= 40) {
        indicator.className = 'accuracy-indicator medium';
        indicator.title = 'Средняя точность. Для улучшения можно провести повторную калибровку';
    } else {
        indicator.className = 'accuracy-indicator low';
        indicator.title = 'Низкая точность. Рекомендуется провести повторную калибровку';
    }
}