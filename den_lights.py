import my_appapi as appapi
             
class den_lights(appapi.my_appapi):

  def initialize(self):
    # self.LOGLEVEL="DEBUG"
    self.log("den_lights App")

    ######################### Values to move to config file or somewhere.
    self.light_max=254
    self.light_dim=128

    self.hi_temp=75
    self.lo_temp=68

    self.targets={"light.den_fan_light":{"triggers":{"light.den_fan_light":{"type":"light","bit":32,"onValue":"on"},
                                                        "input_boolean.someone_home":{"type":"tracker","bit":1,"onValue":"on"},
                                                        "media_player.den_tv":{"type":"media","bit":8,"onValue":"playing"},
                                                        "sensor.den_motion":{"type":"motion","bit":2,"onValue":8}},
                                            "type":"light",
                                            "onState":[34,35,38,39,41,42,43,45,46,47,50,51,54,55,57,58,59,61,62,63,98,99,102,103,105,106,107,109,110,111,114,115,118,119,121,122,123,125,126,127],
                                            "dimState":[100,101,104,108,112,113,116,117,120,124],
                                            "callback":self.light_state_handler,
                                            "overrides":["input_boolean.party_override"]},
                 "light.den_fan":{"triggers":{"light.den_fan":{"type":"fan","bit":32,"onValue":"on"},
                                                     "sensor.den_temperature":{"type":"temperature","bit":8,"onValue":"on"},
                                                     "input_boolean.someone_home":{"type":"tracker","bit":2,"onValue":"home"}},
                                         "type":"fan",
                                         "onState":[4,5,6,7,12,13,14,15,20,21,22,23,28,29,30,31,32,36,37,38,39,44,45,46,47,52,53,54,55,60,61,62,63,68,69,70,71,76,77,78,79,84,85,86,87,92,93,94,95,100,101,102,103,108,109,110,111,116,117,118,119,124,125,126,127],
                                         "dimState":[0],
                                         "callback":self.light_state_handler,
                                         "overrides":["input_boolean.party_override"]}}

    #################End of values to move to config file or somewhere.

    for ent in self.targets:
      for ent_trigger in self.targets[ent]["triggers"]:
        self.log("registering callback for {} on {} for target {}".format(ent_trigger,self.targets[ent]["callback"],ent))
        self.listen_state(self.targets[ent]["callback"],ent_trigger,target=ent)
      self.process_light_state(ent)      # process each light as we register a callback for it's triggers rather than wait for a trigger to fire first.
    self.anyone_home(["device_tracker.scox0129_sc0129","device_tracker.ccox0605_ccox0605","device_tracker.scox1209_scox1209","device_tracker.turboc1208_cc1208"])

  ########
  #
  # state change handler.  All it does is call process_light_state all the work is done there.
  #
  def light_state_handler(self,trigger,attr,old,new,kwargs):
    self.log("trigger = {}, attr={}, old={}, new={}, kwargs={}".format(trigger,attr,old,new,kwargs))
    self.process_light_state(kwargs["target"])


  ########
  #
  # process_light_state.  All the light processing happens in here.
  #
  def process_light_state(self,target,**kwargs):
    # build current state binary flag.
    state=0
    type_bits={}
    
    # here we are building a binary flag/mask that represents the current state of the triggers that impact our target light.
    # one bit for each trigger.
    # bits are assigned in targets dictionary.

    for trigger in self.targets[target]["triggers"]:      # loop through triggers
      self.log("trigger={} type={} onValue={} bit={} currentstate={}".format(trigger,self.targets[target]["triggers"][trigger]["type"],self.targets[target]["triggers"][trigger]["onValue"],
                                                      self.targets[target]["triggers"][trigger]["bit"],self.normalize_state(target,trigger,self.get_state(trigger))))
      # logical "or" value for this trigger to existing state bits.
      state=state | (self.targets[target]["triggers"][trigger]["bit"] if (self.normalize_state(target,trigger,self.get_state(trigger))==self.targets[target]["triggers"][trigger]["onValue"]) else 0)

      # typebits is a quick access array that takes the friendly type of the trigger and associates it with it's bit
      # it's just to make it easier to search later.
      type_bits[self.targets[target]["triggers"][trigger]["type"]]=self.targets[target]["triggers"][trigger]["bit"]


    self.log("state={}".format(state))
    if not self.check_overide_active(target):               # if the override bit is set, then don't evaluate anything else.  Think of it as manual mode.
      if not state in self.targets[target]["onState"]:     # if its not in on its off these states always result in light being turned off
        self.log("state = {} turning off light".format(state))
        self.turn_off(target)
      elif state in self.targets[target]["onState"]:    # these states always result in light being turned on.
        self.log("state = {} turning on light".format(state))
        if state in self.targets[target]["dimState"]:                      # when turning on lights, media player determines whether to dim or not.
          self.log("media player involved so dim lights")
          self.turn_on(target,brightness=self.light_dim)
        else:                                                   # it wasn't a media player dim situation so it's just a simple turn on the light.
          self.log("state={} turning on light".format(state))
          self.turn_on(target,brightness=self.light_max)
    else:
      self.log("home override set so no automations performed")

  #############
  #
  # normalize_state - take incoming states and convert any that are calculated to on/off values.
  #
  def normalize_state(self,target,trigger,newstate):
    if newstate==None:                   # handle a newstate of none, typically means the object didn't exist.
      newstate=self.get_state(target)    # if thats the case, just return the state of the target so nothing changes.

    if type(newstate)==str:                          # deal with a new state that's a string
      if newstate in ["home","house","Home","House"]:  # deal with having multiple versions of house and home to account for.
        newstate="home"
    else:                                            # if it's not a string, we are assuming it's a number.  May not be true, but for now it should be.
      if self.targets[target]["triggers"][trigger]["type"]=="temperature":     # is it a temperature.
        currenttemp = int(float(newstate))           # convert floating point to integer.
        if currenttemp>=hi_temp:                     # handle temp Hi / Low state setting to on/off.  
          newstate="on"
        elif currenttemp<=self.low_temp:
          newstate="off"
        else:
          newstate= self.get_state(target)              # If new state is in between target points, just return current state of target so nothing changes.
      else:                                          # we have a number, but it's not a temperature so leave the value alone.
        self.log("newstate is a number, but not a temperature, so leave it alone : {}".format(newstate))
    return newstate

  def check_overide_active(self,target):
    override_active=False
    for override in self.targets[target]["overrides"]:
      if self.get_state(override)=="on":
        return True

  def anyone_home(self,elist=["device_tracker"]):
    retval=False
    for d in elist:
      self.log("d={}".format(d))
      result=self.get_state(d,attribute=None)
      if isinstance(result,str):     # single result out, must have been full device name entered
        if result in ["home","house"]:
          retval=True
          break
      else:
        for rval in result:
          if result[rval]["state"] in ["home","house"]:
            retval=True
            break
    self.log("retval={}".format(retval))
    return retval 
