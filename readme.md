[seamk_logo]:   /img/seamk_logo.svg
[ely_logo]:     /img/elyfi-logo.png
[euo_logo]:     /img/euo-logo.png 
[agrop_logo]:   /img/agropilotti-logo.png
[webview]:      /img/mapview.jpg

![agrop_logo]

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14637318.svg)](https://doi.org/10.5281/zenodo.14637318)

# Tukiasemien peitto kartalla

Koska hankkeessa koottiin uusia tukiasemia hyvä määrä, kiinnostaa tietenkin tietää minkälaisen kattavuuden RTK korjaussignaalille niillä saatiin. Tässä repositoryssä on muutama python scripti, joilla voi kerätä datan webbisivua varten, joka visualisoi asemien sijainnit sekä piirtää niiden ympärille 40km halkaisijaltaan olevan ympyrän ja erottelee eri casterit väreillä toisistaan.

![webview]

## Toiminnan kuvaus

### Alueen rajaus

`retrieve_border.py` hakee [OpenStreetMapin](https://www.openstreetmap.org/) [Overpass APIn](https://wiki.openstreetmap.org/wiki/Overpass_API) avulla halutun alueen rajat, yksinkertaistaa niitä hieman ja tallentaa sen geojson muodossa haluttuun paikkaan. 

### Asematietojen haku

`update_stations.py` kyselee NTRIP castereilta listaa tukiasemista (sourcetable), suodattaa ne haluttaessa käyttäen edellä haettua geojsonia tai maa-koodia käyttäen. Ohjelmassa on valmius hakea RTK2Go:n, Centipeden ja Emlidin castereista listat. Listaa voi jatkaa peräkkäisillä kyselyillä, joten voi hakea datan erikseen kaikista kolmesta lähteestä.

### Karttanäkymä

`web/basestations.html` on html-sivu, joka käyttää [Leaflet](https://leafletjs.com/)-kirjastoa kartan piirtämiseen. Sivun koodissa määritellään mistä löytyy geojson ja asema lista. Jos geojsonia ei ole määritelty, ei aluerajausta ja sen ulkopuolisen alueen tummennusta piirretä.

`server.py` on simppeli http-palvelin, jolla voi kokeilla sivun näkyvyyttä paikallisesti. Se jakaa oletuksena web hakemiston sisällön portin 8000 kautta. 

## Asennus

Kun olet hakenut repositoryn, voit luoda aluksi python virtuaaliympäristön ja ottaa sen käyttöön.

```
$ python -m venv .venv
$ source .venv/bin/activate
```

Asenna tämän jälkeen tarvittavat paketit.

```
$ pip install --upgrade pip wheel
$ pip install -r requirements.txt
```

Kopioi tämän jälkeen sample.ini:stä varsinainen ntrip.ini tiedosto ja muokkaa sen sisään sopivat tunnukset eri castereille.

```
$ cp sample.ini ntrip.ini
```

## Tietojen päivitys

### Aluerajan haku

`retrieve_border.py` scriptillä voi hakea halutun aluerajan (tai muun alueen kyselyä muokkaamalla). Etelä-Pohjanmaan aluerajojen haku on kovakooodattu scriptiin sisään, jos haluat muuttaa sitä, käy vaihtamassa OVERPASS_QUERY muuttujen sisältöä. Sopivan kyselyn luomisessa auttaa [Overpass Turbo](https://overpass-turbo.eu/), jossa voi käydä kokeilemassa mitä kyselyt palauttavat. `-h` argumentilla saat listan komentorivi parametreista, voit säätää polygonin yksinkertaistamisen toleranssia, jos se jää liian tarkaksi tai tulee liian kulmikkaana ulos. Alla oleva käsky tallentaa aluerajan `web/region.geojson` tiedostoon, mikä on oletus jota webbisivu lukee.

```
$ python retrieve_border.py -o web/region.geojson
```

### Tukiasemien listaus

Tukiasemien listauksien hakeminen castereilta tapahtuu `update_stations.py` scriptillä. Alla oleva komento hakisi sourcetable RTK2Go:sta, suodattaisi pois aluerajan ulkopuolella olevat asemat (mutta ottaa mukaan ne, jotka ovat 20km etäisyydellä rajasta), järjestää ne koordinaattien mukaan luoteesta kaakkoon ja tallentaa listan lopuksi `web/stations.json` tiedostoon (tätä webbisivu oletuksena etsii). Jos tiedosto on jo olemassa, lisätään suodatetut asemat siihen perään, `-a` eli append. `-f` argumentti on varoiksi mukana. Se varmistaa, että oikeasti halutaan hakea data casterilta. Esimerkiksi RTK2Go:ssa bännivasara heiluu helpolla, joten pitää varoa, jottei liian tiuhaan pollaa heidän APIaan. `-r` kertoo mistä alueraja löytyy. `RTK2GO` mitä casteria pollataan, muut vaihtoehdot ovat `CENTIPEDE` ja `EMLID`.

```
$ python update_stations.py -f -a -r web/region.geojson -s coordinates RTK2GO web/stations.json
```

### Visualisointi

Tämän jälkeen voit kopioida web-hakemiston http-palvelimella ja katsella kartalta kattaako RTK tukiasemat itsellesi tärkeät alueet. Jos sinulla ei ole palvelinta, voit ajaa myös `server.py` scriptin, joka käynnistää paikallisen web-palvelimen. Mene sen jälkeen vain selaimella `http://localhost:8000/` osoitteeseen ja näet kartan.

## Agropilotti

Tämä ohjelma luotiin osana Agropilotti hanketta, jossa rakennettiin ja esiteltiin tee-se-itse mahdollisuuksia työkoneiden automaattiohjaukseen. 

---

![euo_logo]

---

![ely_logo]

---

![seamk_logo]
