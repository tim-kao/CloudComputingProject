
function uploadPhoto() {
  var labels = document.getElementById('customLabels').value;
  var file = document.getElementById('file_path').files[0];
  var apigClient = apigClientFactory.newClient({
    apiKey: API_KEY,
  });

  var attached_labels = null
  if (labels){
    attached_labels = labels.split(',');
  }
  console.log(attached_labels);
  var params ={
      "item": file.name,
      "x-amz-meta-customLabels":attached_labels,
      "Content-Type": "application/json",
      "Accept": "application/json"
    };
  var additionalParams = {
    headers: {
      'Content-Type': 'image/jpeg',
    },
  };
  getBase64(file).then(
    data => {
    var body = data.split(',')[1];
    console.log("images:", body)
    apigClient.uploadPut(params, body)
        .then(function(result){
         console.log("Upload OK");
         alert("Upload OK");
          // Add success callback code here.
        }).catch( function(result){
          // Add error callback code here.
          console.log("Upload GG");
          alert("Upload GG");
        });
      })
}

   function getBase64(file) {
     return new Promise((resolve, reject) => {
       const reader = new FileReader();
       reader.readAsDataURL(file);
       reader.onload = () => resolve(reader.result);
       reader.onerror = error => reject(error);
     });
   }
