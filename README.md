## Installation ##

Create a virtual enviroment to install the packages listed in requirements.txt

----------
python3 -m venv .venv

----------
Activate the virtual enviroment using:

-----------
.venv\Scripts\activate

-----------

Next install all packages in the file using:

------------------
pip install -r /path/to/requirements.txt

------------------

Access from a powershell window into the folder you currently have the script Load_API.py
Then just execute the file with python Load_API.py

The API should be running


## USAGE ##

Prepare a json with the correct structure.

Use step by step the following commands on another powershell window.

---------------
$jsonString = Get-Content -Raw -Path "Path/to/your/Json/file" #Modify with the path of the actual json
$jsonObject = ConvertFrom-Json $jsonString

$load = $jsonObject.load
$fuels = $jsonObject.fuels
$powerplants = $jsonObject.powerplants

$body = $jsonObject | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8888/productionplan" -Method Post -Body $body -Headers $headers -ContentType "application/json"

$response | ConvertTo-Json

----------------------

Another way is to change the file "POST_Json.txt" for "POST_Json.ps1" and then modifiy the following text "Path/to/your/Json/file" with the actual path to your json file
From another powershell window execute "POST_Json.ps1" using the following command:

-------------------------
./POST_Json.ps1
