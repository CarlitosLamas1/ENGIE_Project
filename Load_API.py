from flask import Flask, jsonify, request
import pandas as pd
import numpy as np

app = Flask(__name__)

@app.route('/productionplan', methods=['POST'])
def production_plan():
    try:
        data = request.get_json()  # Get the JSON data from the request body
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Read and fill information
        load = data["load"]
        fossilMinUsage = load
        fuels = data["fuels"]
        powerPlants = data["powerplants"]

        # Información preliminar
        co2PerMW = 0.3
        windEff = fuels["wind(%)"]/100 # Extracción de la eficiencia del viento ese día
        mwPricePerfKerorsineL = fuels["kerosine(euro/MWh)"]
        co2PerTonPrice = fuels["co2(euro/ton)"]
        mwPricePerGasL = fuels["gas(euro/MWh)"] + co2PerTonPrice*co2PerMW

        # Types of generators 
        outputData = []
        keys = ["Type", "Plant", "Eff", "FuelPrice", "Pmin", "Pmax", "Price", "Load", "Tier"]
        allfossilGens = pd.DataFrame(columns=keys)

        pmaxWind = 0
        pMax = 0
        pMinIndv = -1
        for item in powerPlants:
            typeGen = item["type"]
            match typeGen:
                case "gasfired":
                    allfossilGens.loc[len(allfossilGens)] = ["Gas", item["name"], item["efficiency"], mwPricePerGasL, item["pmin"], item["pmax"],0, 0, -1]
                    pMax = pMax + item["pmax"]
                    pMinIndv = item["pmin"] if pMinIndv < 0 or pMinIndv > item["pmin"] else pMinIndv
                case "turbojet":
                    allfossilGens.loc[len(allfossilGens)] = ["Kerosine", item["name"], item["efficiency"], mwPricePerfKerorsineL, item["pmin"], item["pmax"], 0, 0, -1]
                    pMax = pMax + item["pmax"]
                    pMinIndv = item["pmin"] if pMinIndv < 0 or pMinIndv > item["pmin"] else pMinIndv
                case "windturbine":
                    windUsage = round(item["pmax"]*windEff*10)/10 if round(item["pmax"]*windEff*10)/10 <= fossilMinUsage else fossilMinUsage
                    allfossilGens.loc[len(allfossilGens)] = ["Wind", item["name"], item["efficiency"], 0, item["pmin"], item["pmax"], 0, windUsage, -1]
                    fossilMinUsage = round((fossilMinUsage - windUsage)*10)/10
                    pmaxWind = pmaxWind + round(item["pmax"]*windEff*10)/10
                    pMax = pMax + round(item["pmax"]*windEff*10)/10

        if pMax < load:
            return jsonify({"error": f"More load requested ({load}MW) than the maximum available ({pMax}MW)."}), 400
        elif pmaxWind < load and pMinIndv > load:
            return jsonify({"error": f"Less load requested ({load}MW) than the minimum necessary ({pMinIndv}MW)."}), 400
        
        #Máxima cantidad de kerosine que sería más barata en vez de usar todo el Pmin del Gas.        
        allfossilGens = allfossilGens.sort_values(by=['Eff', 'FuelPrice', 'Pmin'], ascending=[False, True, False])
        allfossilGens['Price'] = np.where(allfossilGens['Pmin'] < fossilMinUsage, fossilMinUsage, allfossilGens['Pmin']) * allfossilGens['FuelPrice'] / allfossilGens['Eff']
        allfossilGens = allfossilGens.reset_index(drop=True)
        for i in range(0, len(allfossilGens)):
            if i == 0:
                allfossilGens.loc[i, "Tier"] = 1
            elif allfossilGens.loc[i, "Eff"] == allfossilGens.loc[i-1,"Eff"] and allfossilGens.loc[i, "FuelPrice"] == allfossilGens.loc[i-1, "FuelPrice"] and allfossilGens.loc[i, "Pmin"] == allfossilGens.loc[i-1, "Pmin"]:
                allfossilGens.loc[i, "Tier"] = allfossilGens.loc[i-1, "Tier"]
            else:
                allfossilGens.loc[i, "Tier"] = allfossilGens.loc[i-1, "Tier"] + 1


        load = fossilMinUsage
        tier = 2
        while fossilMinUsage > 0:
            bestIndex = allfossilGens[(allfossilGens["Tier"]>=tier) & (allfossilGens["Pmax"]>0)]["Price"].idxmin()
            if allfossilGens.iloc[bestIndex]["Pmin"] < fossilMinUsage and allfossilGens.iloc[bestIndex]["Tier"]==tier:
                minSums = allfossilGens[allfossilGens['Tier'] == tier]['Pmin'].sum()
                maxSums = allfossilGens[allfossilGens['Tier'] == tier]['Pmax'].sum()
                maxIndv = allfossilGens[allfossilGens['Tier'] == tier].iloc[0]['Pmax']
                minIndv = allfossilGens[allfossilGens['Tier'] == tier].iloc[0]['Pmin']
                
                if maxIndv >= fossilMinUsage and minIndv <= fossilMinUsage:
                    allfossilGens.loc[bestIndex, "Load"] = fossilMinUsage
                    fossilMinUsage = 0
                elif maxIndv < fossilMinUsage and maxSums >= fossilMinUsage and minSums<=fossilMinUsage:
                    nTierSeleted = len(allfossilGens[allfossilGens['Tier'] == tier])
                    allfossilGens.loc[allfossilGens['Tier'] == tier, 'Load'] = round(fossilMinUsage/nTierSeleted*10)/10
                    sumS = allfossilGens[allfossilGens["Tier"]==tier]["Load"].sum()
                    if sumS > fossilMinUsage:
                        allfossilGens.loc[bestIndex, "Load"] = allfossilGens.loc[bestIndex, "Load"] - (sumS - fossilMinUsage)
                    elif sumS < fossilMinUsage:
                        allfossilGens.loc[bestIndex, "Load"] = allfossilGens.loc[bestIndex, "Load"] + (fossilMinUsage - sumS)
                    fossilMinUsage=0
                elif maxSums < fossilMinUsage:
                    nTierSeleted = len(allfossilGens[allfossilGens['Tier'] == tier])
                    allfossilGens.loc[allfossilGens['Tier'] == tier, 'Load'] = allfossilGens.loc[allfossilGens['Tier'] == tier, 'Pmax']
                    fossilMinUsage=round((fossilMinUsage-maxSums)*10)/10
                    tier = tier + 1
                    allfossilGens.loc[allfossilGens['Tier'] >= tier, 'Price'] = np.where(allfossilGens['Pmin'] < fossilMinUsage, fossilMinUsage, allfossilGens['Pmin']) * allfossilGens['FuelPrice'] / allfossilGens['Eff']

            elif allfossilGens.iloc[bestIndex]["Pmin"] >= fossilMinUsage:
                allfossilGens.loc[bestIndex, "Load"] = allfossilGens.iloc[bestIndex]["Pmin"]
                excess = round((allfossilGens.loc[bestIndex, "Pmin"] - fossilMinUsage)*10)/10
                indexCount = 0
                tierAux = tier-1
                while excess > 0 and tier >= 0:                    
                    filteredData = allfossilGens[allfossilGens["Tier"]==tierAux]["Load"]
                    try:
                        indexMin = filteredData.nlargest(indexCount+1).index[indexCount]
                    except:
                        if tierAux > 0:
                            tierAux = tierAux - 1
                            indexCount = 0
                            indexMin = filteredData.nlargest(indexCount+1).index[indexCount]
                        else:
                            break                                      
                
                    if allfossilGens.loc[indexMin, "Load"] - excess >= allfossilGens.loc[indexMin, "Pmin"]:
                        allfossilGens.loc[indexMin, "Load"] = round((allfossilGens.loc[indexMin, "Load"] - excess)*10)/10
                        excess = 0
                    else:
                        excess = round((excess - (allfossilGens.loc[indexMin, "Load"] - allfossilGens.loc[indexMin, "Pmin"]))*10)/10
                        allfossilGens.loc[indexMin, "Load"] = allfossilGens.loc[indexMin, "Pmin"]
                        indexCount = indexCount + 1                
                fossilMinUsage = 0

            else:
                allfossilGens.loc[bestIndex, "Load"] = fossilMinUsage
                fossilMinUsage = 0

        for index, item in allfossilGens.iterrows():
            outputData.append({"name": f"{item['Plant']}", "p": item['Load']})

        return jsonify(outputData), 200  # Return the processed data as JSON

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, port=8888)