const {chromium}=require(process.env.BROWSER_HOME+"/node_modules/playwright-core");
const assert=require("node:assert/strict");
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.BROWSER_HOME+"/chrome-headless-shell-win64/chrome-headless-shell.exe",headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on("pageerror",e=>errors.push(e.message));
  await page.addInitScript(()=>Object.defineProperty(crypto,"randomUUID",{value:undefined}));
  const url=process.env.TEST_URL;
  await page.goto(url);
  await page.getByText("Gesamtspeicher",{exact:true}).waitFor();
  assert.match(await page.getByTestId("storage-aggregate").innerText(),/60/);
  assert.match(await page.getByTestId("storage-aggregate").innerText(),/9/);
  assert.equal(await page.getByRole("meter").count(),3);
  const settings=await page.request.get(url+"/api/settings").then(r=>r.json());
  assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--background").trim()),"#101216");
  await page.getByText(/Geräte und Unterknoten/).nth(1).click();
  await page.getByText(/Geräte und Unterknoten/).nth(2).click();
  await page.getByRole("textbox",{name:"Geräte suchen"}).fill("Verbraucher 49");
  await page.locator('[data-testid^="flow-card-"]').getByText("Verbraucher 49",{exact:true}).waitFor();
  await page.screenshot({path:"work/modular-desktop.png",fullPage:true});
  await page.goto(url+"/datenerfassung");
  await page.getByRole("heading",{name:"Messpunkte und Diagnose"}).waitFor();
  await page.getByRole("button",{name:"Verbindung hinzufügen",exact:true}).click();
  await page.getByLabel("Name",{exact:true}).fill("Browser Verbindung");
  await page.getByLabel("Host / IP").fill("127.0.0.1");
  await page.getByLabel("Aktiv",{exact:true}).uncheck();
  await page.getByRole("button",{name:"Speichern",exact:true}).click();
  await page.getByText("Browser Verbindung",{exact:true}).waitFor();
  await page.getByRole("button",{name:"Messpunkt hinzufügen",exact:true}).click();
  await page.getByLabel("Name",{exact:true}).fill("Browser Messpunkt");
  await page.getByLabel("Verbindung",{exact:true}).selectOption({label:"Browser Verbindung"});
  await page.getByLabel("MQTT-Topic (exakt)").fill("browser/test");
  await page.getByRole("button",{name:"Speichern",exact:true}).click();
  await page.getByRole("textbox",{name:"Messpunkte suchen"}).fill("Browser Messpunkt");
  await page.getByText("Browser Messpunkt",{exact:true}).waitFor();
  const motor=await page.request.get(url+"/api/measurements").then(r=>r.json()).then(points=>points.find(p=>p.id==="motor"));
  await page.request.put(url+"/api/measurements/motor",{data:{...motor,name:"m".repeat(100)}});
  await page.goto(url+"/konfiguration");
  await page.getByTestId("add-flow-button").click();
  const symbols=page.getByTestId("flow-editor-icon-grid").getByRole("button");
  assert.ok(await symbols.count()>50);
  await page.getByPlaceholder("Symbole suchen").fill("Aquarium");
  assert.equal(await symbols.count(),1);
  await page.getByTestId("flow-editor-tab-datapoints").click();
  await page.getByTestId("flow-editor-dp-power_total").fill("point:motor");
  await page.getByTestId("flow-editor-tab-general").click();
  assert.equal(await page.getByTestId("flow-editor-name-input").inputValue(),"m".repeat(60));
  await page.getByTestId("flow-editor-cancel-button").click();
  for(const layout of ["square","rounded","flow"]){
   await page.goto(url+"/darstellung");
   await page.getByRole("button",{name:layout==="square"?/Kompakt \/ eckig/:layout==="rounded"?/Modern \/ Karten/:/Flussdiagramm/}).click();
   await page.getByRole("button",{name:"Darstellung speichern"}).click();
   await page.waitForFunction(layout=>document.documentElement.dataset.layout===layout,layout);
   await page.goto(url);
   await page.getByText("Gesamtspeicher",{exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.dataset.layout),layout);
  }
  await page.goto(url+"/flow");
  await page.getByText("Gesamtspeicher",{exact:true}).waitFor();
  assert.equal(await page.locator("header,nav").count(),0);
  await page.setViewportSize({width:390,height:844});
  for(const path of ["/flow","/","/datenerfassung","/darstellung","/konfiguration","/system","/energie"]){
   await page.goto(url+path);await page.waitForTimeout(350);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),`horizontal overflow ${path}`);
  }
  await page.goto(url+"/flow");await page.getByText("Gesamtspeicher",{exact:true}).waitFor();
  await page.screenshot({path:"work/modular-mobile.png",fullPage:true});
  assert.deepEqual(errors,[]);
  await page.request.put(url+"/api/settings",{data:settings});
  console.log("Chromium: registry forms, HTTP ID fallback, symbols, name mapping, 3 layouts, embed, mobile routes and no JS errors OK");
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
