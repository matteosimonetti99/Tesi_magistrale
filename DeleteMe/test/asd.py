import xml.etree.ElementTree as ET

# Your XML content (replace with your actual XML file content)
XML = '''
   <process id="sid-e138ad92-53db-4474-a117-cf3a5074182e" isExecutable="false">
      <startEvent id="sid-477D1DF3-C5FC-460F-8AD1-03D4B7C26FB6" name="Credit application received">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <outgoing>sid-E469684F-C09F-4A8B-A916-E9927BA15372</outgoing>
         <documentation id="96b04510-7bb2-0f54-f94c-dffc5deca53c">
            {"arrivalRateDistribution":{"type":"exponential","mean":1800,"value":0,"stdev":0,"min":0,"max":0,"timeUnit":"minutes"},"instances":"5000","resources":{"Clerk":{"name":"Clerk","costPerHour":"25","amount":"3"},"CreditOfficer":{"name":"Credit
            Officer","costPerHour":"50","amount":"3"},"System":{"name":"System","costPerHour":"0","amount":"1"}},"startAt":"2012-08-03
            17:27:09","timetable":{"Clerk":{"Mon-Fri":"09:00:00-17:00:00"},"CreditOfficer":{"Mon-Fri":"09:00:00-17:00:00"}},"currency":"EUR"}</documentation>
      </startEvent>
      <parallelGateway gatewayDirection="Diverging" id="sid-6B518C80-2B96-4C95-B6DE-F9E4A75FF191"
         name="">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-E469684F-C09F-4A8B-A916-E9927BA15372</incoming>
         <outgoing>sid-6FD4FFD3-5784-4D33-9509-234EAB886930</outgoing>
         <outgoing>sid-9E95A790-241E-4629-8D67-E9A2CE55E3DC</outgoing>
      </parallelGateway>
      <task completionQuantity="1" id="sid-4B24111F-B305-4608-9E12-744B47C44D0D"
         isForCompensation="false" name="Check credit history" startQuantity="1">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffcc" />
            <signavio:signavioMetaData metaKey="risklevel" metaValue="" />
            <signavio:signavioMetaData metaKey="externaldocuments" metaValue="[]" />
         </extensionElements>
         <incoming>sid-6FD4FFD3-5784-4D33-9509-234EAB886930</incoming>
         <outgoing>sid-10E6C62E-2CBD-476A-976B-B862156F5DEC</outgoing>
         <documentation id="a7411ebb-eb59-99af-9256-8ae109dbac3a">{"durationDistribution":{"type":"normal","mean":600,"value":3600,"stdev":120,"min":0,"max":0,"timeUnit":"minutes"},"resource":"Clerk","fixedCost":"0","name":"Check
            credit history"}</documentation>
      </task>
      <parallelGateway gatewayDirection="Converging" id="sid-A4FBE0D9-8D45-4B22-8D7C-217BEBBA3B06"
         name="">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-FF95F9DA-C10F-455B-B2FC-FBC1C270C0B4</incoming>
         <incoming>sid-10E6C62E-2CBD-476A-976B-B862156F5DEC</incoming>
         <outgoing>sid-281400BA-53E3-47C9-8437-B699CA182453</outgoing>
      </parallelGateway>
      <task completionQuantity="1" id="sid-D048D99D-F549-43B8-8ACB-5AE153B12B0F"
         isForCompensation="false" name="Check income sources" startQuantity="1">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffcc" />
            <signavio:signavioMetaData metaKey="risklevel" metaValue="" />
            <signavio:signavioMetaData metaKey="externaldocuments" metaValue="[]" />
         </extensionElements>
         <incoming>sid-9E95A790-241E-4629-8D67-E9A2CE55E3DC</incoming>
         <outgoing>sid-FF95F9DA-C10F-455B-B2FC-FBC1C270C0B4</outgoing>
         <documentation id="92bbac3d-8125-04be-c42f-716fd33ea0d8">{"durationDistribution":{"type":"normal","mean":"20","value":"0","stdev":"4","min":"0","max":"0","timeUnit":"seconds"},"resource":"Clerk","fixedCost":"0","name":"Check
            income sources"}</documentation>
      </task>
      <exclusiveGateway gatewayDirection="Converging" id="sid-5CD7112A-35AE-483D-95BC-EC8270DA9A39"
         name="">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-281400BA-53E3-47C9-8437-B699CA182453</incoming>
         <incoming>sid-AFEC7074-8C12-43E2-A1FE-87D5CEF395C8</incoming>
         <outgoing>sid-0617E6F8-139D-4F02-B850-6604A21D603D</outgoing>
      </exclusiveGateway>
      <exclusiveGateway default="sid-AE313010-5715-438C-AD61-1C02F03DCF77"
         gatewayDirection="Diverging" id="sid-FACFF0AE-6A1B-47AC-B289-F5E60CB12B2A" name="">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-0B638436-AEB9-459C-AC18-9B64381CB7F9</incoming>
         <outgoing>sid-AFEC7074-8C12-43E2-A1FE-87D5CEF395C8</outgoing>
         <outgoing>sid-AE313010-5715-438C-AD61-1C02F03DCF77</outgoing>
      </exclusiveGateway>
      <task completionQuantity="1" id="sid-3744BAA1-9382-4FAB-B7FE-B6A333F10D25"
         isForCompensation="false" name="Receive customer feedback" startQuantity="1">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffcc" />
            <signavio:signavioMetaData metaKey="risklevel" metaValue="" />
            <signavio:signavioMetaData metaKey="externaldocuments" metaValue="[]" />
         </extensionElements>
         <incoming>sid-58A4F70B-5279-4DBC-AEE2-8D7D2596DE63</incoming>
         <outgoing>sid-0B638436-AEB9-459C-AC18-9B64381CB7F9</outgoing>
         <documentation id="828ce122-8c92-a007-6824-e8bce3308d7b">{"durationDistribution":{"type":"fixed","mean":"0","value":"0","stdev":"0","min":"0","max":"0","timeUnit":"seconds"},"resource":"System","fixedCost":"0","name":"Receive
            customer feedback"}</documentation>
      </task>
      <task completionQuantity="1" id="sid-622A1118-4766-43B2-A004-7DADE521982D"
         isForCompensation="false" name="Notify rejection" startQuantity="1">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffcc" />
            <signavio:signavioMetaData metaKey="risklevel" metaValue="" />
            <signavio:signavioMetaData metaKey="externaldocuments" metaValue="[]" />
         </extensionElements>
         <incoming>sid-8AE82A7B-75EE-401B-8ABE-279FB05A3946</incoming>
         <outgoing>sid-58A4F70B-5279-4DBC-AEE2-8D7D2596DE63</outgoing>
         <documentation id="ccaf3372-1cf9-00a9-a7ac-93179ce2300b">{"durationDistribution":{"type":"normal","mean":"10","value":"0","stdev":"2","min":"0","max":"0","timeUnit":"seconds"},"resource":"CreditOfficer","fixedCost":"0","name":"Notify
            rejection"}</documentation>
      </task>
      <exclusiveGateway gatewayDirection="Diverging" id="sid-64FC5B46-47E5-4940-A0AF-ECE87483967D"
         name="">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-FA2D48D3-A316-4C2F-90DB-C2390990D727</incoming>
         <outgoing>sid-8AE82A7B-75EE-401B-8ABE-279FB05A3946</outgoing>
         <outgoing>sid-789335C6-205C-4A03-9AD6-9655893C1FFB</outgoing>
      </exclusiveGateway>
      <task completionQuantity="1" id="sid-02577CBF-ABA3-4EFD-9480-E1DFCF238B1C"
         isForCompensation="false" name="Assess application" startQuantity="1">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffcc" />
            <signavio:signavioMetaData metaKey="risklevel" metaValue="" />
            <signavio:signavioMetaData metaKey="externaldocuments" metaValue="[]" />
         </extensionElements>
         <incoming>sid-0617E6F8-139D-4F02-B850-6604A21D603D</incoming>
         <outgoing>sid-FA2D48D3-A316-4C2F-90DB-C2390990D727</outgoing>
         <documentation id="6570aa14-a78f-5baa-3252-345be7df4756">{"durationDistribution":{"type":"exponential","mean":1200,"value":0,"stdev":0,"min":0,"max":0,"timeUnit":"minutes"},"resource":"CreditOfficer","fixedCost":"0","name":"Assess
            application"}</documentation>
      </task>
      <task completionQuantity="1" id="sid-503A048D-6344-446A-8D67-172B164CF8FA"
         isForCompensation="false" name="Make credit offer" startQuantity="1">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffcc" />
            <signavio:signavioMetaData metaKey="risklevel" metaValue="" />
            <signavio:signavioMetaData metaKey="externaldocuments" metaValue="[]" />
         </extensionElements>
         <incoming>sid-789335C6-205C-4A03-9AD6-9655893C1FFB</incoming>
         <outgoing>sid-E27B9A7A-4414-4BFC-83F5-4BC438B77E37</outgoing>
         <documentation id="7baa834e-7c36-56af-ea8f-7ee1dd9e3f5a">{"durationDistribution":{"type":"normal","mean":"10","value":"30","stdev":"2","min":"0","max":"0","timeUnit":"seconds"},"resource":"CreditOfficer","fixedCost":"0","name":"Make
            credit offer"}</documentation>
      </task>
      <exclusiveGateway gatewayDirection="Converging" id="sid-F9CBAF0E-0679-4E1F-ACE1-E98177DDA3D0"
         name="">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-E27B9A7A-4414-4BFC-83F5-4BC438B77E37</incoming>
         <incoming>sid-AE313010-5715-438C-AD61-1C02F03DCF77</incoming>
         <outgoing>sid-287B8ED1-E9CD-44BD-92E8-C9AD7E940100</outgoing>
      </exclusiveGateway>
      <endEvent id="sid-08B606A8-2F7C-4DFD-BEA8-A0F4694AA576" name="Credit application processed">
         <extensionElements>
            <signavio:signavioMetaData metaKey="bgcolor" metaValue="#ffffff" />
         </extensionElements>
         <incoming>sid-287B8ED1-E9CD-44BD-92E8-C9AD7E940100</incoming>
      </endEvent>
      <sequenceFlow id="sid-6FD4FFD3-5784-4D33-9509-234EAB886930" name=""
         sourceRef="sid-6B518C80-2B96-4C95-B6DE-F9E4A75FF191"
         targetRef="sid-4B24111F-B305-4608-9E12-744B47C44D0D" />
      <sequenceFlow id="sid-9E95A790-241E-4629-8D67-E9A2CE55E3DC" name=""
         sourceRef="sid-6B518C80-2B96-4C95-B6DE-F9E4A75FF191"
         targetRef="sid-D048D99D-F549-43B8-8ACB-5AE153B12B0F" />
      <sequenceFlow id="sid-FF95F9DA-C10F-455B-B2FC-FBC1C270C0B4" name=""
         sourceRef="sid-D048D99D-F549-43B8-8ACB-5AE153B12B0F"
         targetRef="sid-A4FBE0D9-8D45-4B22-8D7C-217BEBBA3B06" />
      <sequenceFlow id="sid-10E6C62E-2CBD-476A-976B-B862156F5DEC" name=""
         sourceRef="sid-4B24111F-B305-4608-9E12-744B47C44D0D"
         targetRef="sid-A4FBE0D9-8D45-4B22-8D7C-217BEBBA3B06" />
      <sequenceFlow id="sid-281400BA-53E3-47C9-8437-B699CA182453" name=""
         sourceRef="sid-A4FBE0D9-8D45-4B22-8D7C-217BEBBA3B06"
         targetRef="sid-5CD7112A-35AE-483D-95BC-EC8270DA9A39" />
      <sequenceFlow id="sid-FA2D48D3-A316-4C2F-90DB-C2390990D727" name=""
         sourceRef="sid-02577CBF-ABA3-4EFD-9480-E1DFCF238B1C"
         targetRef="sid-64FC5B46-47E5-4940-A0AF-ECE87483967D" />
      <sequenceFlow id="sid-E27B9A7A-4414-4BFC-83F5-4BC438B77E37" name=""
         sourceRef="sid-503A048D-6344-446A-8D67-172B164CF8FA"
         targetRef="sid-F9CBAF0E-0679-4E1F-ACE1-E98177DDA3D0" />
      <sequenceFlow id="sid-287B8ED1-E9CD-44BD-92E8-C9AD7E940100" name=""
         sourceRef="sid-F9CBAF0E-0679-4E1F-ACE1-E98177DDA3D0"
         targetRef="sid-08B606A8-2F7C-4DFD-BEA8-A0F4694AA576" />
      <sequenceFlow id="sid-8AE82A7B-75EE-401B-8ABE-279FB05A3946" name="denied"
         sourceRef="sid-64FC5B46-47E5-4940-A0AF-ECE87483967D"
         targetRef="sid-622A1118-4766-43B2-A004-7DADE521982D">
         <conditionExpression xsi:type="tFormalExpression"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">0.2</conditionExpression>
      </sequenceFlow>
      <sequenceFlow id="sid-E469684F-C09F-4A8B-A916-E9927BA15372" name=""
         sourceRef="sid-477D1DF3-C5FC-460F-8AD1-03D4B7C26FB6"
         targetRef="sid-6B518C80-2B96-4C95-B6DE-F9E4A75FF191" />
      <sequenceFlow id="sid-58A4F70B-5279-4DBC-AEE2-8D7D2596DE63" name=""
         sourceRef="sid-622A1118-4766-43B2-A004-7DADE521982D"
         targetRef="sid-3744BAA1-9382-4FAB-B7FE-B6A333F10D25" />
      <sequenceFlow id="sid-0B638436-AEB9-459C-AC18-9B64381CB7F9" name=""
         sourceRef="sid-3744BAA1-9382-4FAB-B7FE-B6A333F10D25"
         targetRef="sid-FACFF0AE-6A1B-47AC-B289-F5E60CB12B2A" />
      <sequenceFlow id="sid-AFEC7074-8C12-43E2-A1FE-87D5CEF395C8" name="decision review requested"
         sourceRef="sid-FACFF0AE-6A1B-47AC-B289-F5E60CB12B2A"
         targetRef="sid-5CD7112A-35AE-483D-95BC-EC8270DA9A39">
         <extensionElements>
            <signavio:signavioLabel align="left" bottom="false" distance="-7.0" from="1"
               left="false" orientation="ll" ref="text_name" right="false" to="2" top="false"
               valign="bottom" x="1003.4727728225834" y="577.0" />
         </extensionElements>
         <conditionExpression xsi:type="tFormalExpression"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">0.2</conditionExpression>
      </sequenceFlow>
      <sequenceFlow id="sid-AE313010-5715-438C-AD61-1C02F03DCF77" name=""
         sourceRef="sid-FACFF0AE-6A1B-47AC-B289-F5E60CB12B2A"
         targetRef="sid-F9CBAF0E-0679-4E1F-ACE1-E98177DDA3D0">
         <conditionExpression xsi:type="tFormalExpression"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">0.8</conditionExpression>
      </sequenceFlow>
      <sequenceFlow id="sid-0617E6F8-139D-4F02-B850-6604A21D603D" name=""
         sourceRef="sid-5CD7112A-35AE-483D-95BC-EC8270DA9A39"
         targetRef="sid-02577CBF-ABA3-4EFD-9480-E1DFCF238B1C" />
      <sequenceFlow id="sid-789335C6-205C-4A03-9AD6-9655893C1FFB" name="granted"
         sourceRef="sid-64FC5B46-47E5-4940-A0AF-ECE87483967D"
         targetRef="sid-503A048D-6344-446A-8D67-172B164CF8FA">
         <conditionExpression xsi:type="tFormalExpression"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">0.8</conditionExpression>
      </sequenceFlow>
      <association associationDirection="None" id="sid-116890D9-47C5-4CFD-A8E5-686BE2F6419F"
         sourceRef="sid-AE313010-5715-438C-AD61-1C02F03DCF77"
         targetRef="sid-1338180C-22E1-4827-A59B-1010B9523606" />
      <association associationDirection="None" id="sid-25F39399-1C15-4602-B512-B2A331CB9A36"
         sourceRef="sid-0617E6F8-139D-4F02-B850-6604A21D603D"
         targetRef="sid-330CE8DA-E292-444E-8D54-B539BFC754FB" />
      <association associationDirection="None" id="sid-D0D7001B-5E95-4F04-BCBB-FA1B2D82989C"
         targetRef="sid-1A1CBF35-09B6-4BE4-AED6-2B3C2867B1A7" />
      <textAnnotation id="sid-1338180C-22E1-4827-A59B-1010B9523606" textFormat="text/plain">
         <text>exit point</text>
      </textAnnotation>
      <textAnnotation id="sid-330CE8DA-E292-444E-8D54-B539BFC754FB" textFormat="text/plain">
         <text>entry point</text>
      </textAnnotation>
      <textAnnotation id="sid-1A1CBF35-09B6-4BE4-AED6-2B3C2867B1A7" textFormat="text/plain">
         <text>exit point</text>
      </textAnnotation>
   </process>
'''

# Parse the XML
root = ET.fromstring(XML)

# Add "bpmn:" prefix to all opening and closing tags
for elem in root.iter():
    elem.tag = f"bpmn:{elem.tag}"

# Convert modified XML back to a string
modified_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")

print(modified_xml)
