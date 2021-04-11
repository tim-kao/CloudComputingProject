// connect to api sdk client
var apigClient = apigClientFactory.newClient();

// Search text in searchbar when search button pressed
$(function() { 
  $('#unitOptions').change(function() {
    let timeOptions = document.getElementById('timeOptions');
    timeOptions.innerHTML = "";
    if ($(this).val() == 'm') {
      let times = ['1', '3'];
      for ( let i = 0; i < times.length; i++) {
        let opt = document.createElement('option');
        opt.innerHTML = times[i];
        opt.value = times[i];
        timeOptions.appendChild(opt);
      }
    }
    else {
      let times = ['5'];
      for ( let i = 0; i < times.length; i++) {
        let opt = document.createElement('option');
        opt.innerHTML = times[i];
        opt.value = times[i];
        timeOptions.appendChild(opt);
      }
    }
  }).change(); // Trigger the event
});

$('#searchbtn').click(function(){
  query = $('#searchbar').val();
  timeNumber = $('#timeOptions').val();
  unitVal = $('#unitOptions').val();
  params = {q: query, unit: unitVal, time: timeNumber};
  console.log(params)
  apigClient.userGet(params, {}, {})
    .then(function(result){
      // Add success callback code here.
      console.log("SUCCESS CALLBACK")
      console.log(result.data)

      var elements = document.getElementsByClassName("subheader");
      for (let i = 0; i < elements.length; i++ ) {
        elements[i].style.display = "block";
      }

      // popChart(result.data)
      // popularity
      popChart(result.data[0], chartdiv0)
      // sentiment
      popChart(result.data[1], chartdiv1)
      popChart(result.data[2], chartdiv2)
      popChart(result.data[3], chartdiv3)
      popChart(result.data[4], chartdiv4)
      // emotion
      popChart(result.data[5], chartdiv5)
      popChart(result.data[6], chartdiv6)
      popChart(result.data[7], chartdiv7)
      popChart(result.data[8], chartdiv8)
      popChart(result.data[9], chartdiv9)


    }).catch(function(result){
      // Add error callback code here.
      console.log("UNSUCCESS CALLBACK")
      console.log(result.data)
    });
    
  });


function popChart(apiData, divId){

  am4core.ready(function() {

  // Themes begin
  am4core.useTheme(am4themes_animated);
  // Themes end

  // Create chart instance
  var chart = am4core.create(divId, am4charts.XYChart);

  // Enable chart cursor
  chart.cursor = new am4charts.XYCursor();
  chart.cursor.lineX.disabled = true;
  chart.cursor.lineY.disabled = true;

  // Enable scrollbar
  chart.scrollbarX = new am4core.Scrollbar();

  // Add data

  chart.data = apiData

  // Create axes
  var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
  dateAxis.renderer.grid.template.location = 0.5;
  dateAxis.dateFormatter.inputDateFormat = "yyyy-MM-dd";
  dateAxis.renderer.minGridDistance = 40;
  dateAxis.tooltipDateFormat = "MMM dd, yyyy";
  dateAxis.dateFormats.setKey("day", "dd");

  var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());

  // Create series
  var series = chart.series.push(new am4charts.LineSeries());
  series.tooltipText = "{date}\n[bold font-size: 17px]value: {valueY}[/]";
  series.dataFields.valueY = "value";
  series.dataFields.dateX = "date";
  series.strokeDasharray = 3;
  series.strokeWidth = 2
  series.strokeOpacity = 0.3;
  series.strokeDasharray = "3,3"

  var bullet = series.bullets.push(new am4charts.CircleBullet());
  bullet.strokeWidth = 2;
  bullet.stroke = am4core.color("#fff");
  bullet.setStateOnChildren = true;
  bullet.propertyFields.fillOpacity = "opacity";
  bullet.propertyFields.strokeOpacity = "opacity";

  var hoverState = bullet.states.create("hover");
  hoverState.properties.scale = 1.7;

  function createTrendLine(data) {
  var trend = chart.series.push(new am4charts.LineSeries());
  trend.dataFields.valueY = "value";
  trend.dataFields.dateX = "date";
  trend.strokeWidth = 2
  trend.stroke = trend.fill = am4core.color("#c00");
  trend.data = data;

  var bullet = trend.bullets.push(new am4charts.CircleBullet());
  bullet.tooltipText = "{date}\n[bold font-size: 17px]value: {valueY}[/]";
  bullet.strokeWidth = 2;
  bullet.stroke = am4core.color("#fff")
  bullet.circle.fill = trend.stroke;

  var hoverState = bullet.states.create("hover");
  hoverState.properties.scale = 1.7;

  return trend;
  };

  // createTrendLine([
  //   { "date": "2012-01-02", "value": 10 },
  //   { "date": "2012-01-11", "value": 19 }
  // ]);

  // var lastTrend = createTrendLine([
  //   { "date": "2012-01-17", "value": 16 },
  //   { "date": "2012-01-22", "value": 10 }
  // ]);

  // Initial zoom once chart is ready
  // lastTrend.events.once("datavalidated", function(){
  // series.xAxis.zoomToDates(new Date(2012, 0, 2), new Date(2012, 0, 13));
  // });

  }); // end am4core.ready()
}