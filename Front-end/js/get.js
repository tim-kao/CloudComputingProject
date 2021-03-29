

function search() {

  var apigClient = apigClientFactory.newClient({
    apiKey: API_KEY
  });
  var keyword = document.getElementById("note-textarea").value;
  if(keyword == "")
    var keyword = textBox.value;
  console.log(keyword);

  var body = {};
  var params = {
    q: keyword,
    'X-Api-Key': API_KEY
  };
  var additionalParams = {
    headers: {
      'Content-Type': "application/json",
    },
  };

  apigClient.userGet(params, body)
    .then(function (result) {
      var body = result.data;
      if (body['statusCode']==200) {
        console.log(body.body);
        var dataPoints = body.body;
        var chart = new CanvasJS.Chart("chartContainer",{
        	title:{
        		text:"Rendering Chart with dataPoints from External JSON"
        	},
        	data: [{
        		type: "line",
        		dataPoints : dataPoints,
        	}]
        });
        $.getJSON("https://canvasjs.com/services/data/datapoints.php?xstart=1&ystart=10&length=100&type=json", function(data) {
        	$.each(data, function(key, value){
        		dataPoints.push({x: value[0], y: parseInt(value[1])});
        	});
        	chart.render();
        });
      }
      else {
        document.getElementById("search_result").innerHTML = "Search not found";
      };
    })
}
