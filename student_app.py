import sounddevice as sd, numpy as np, wave, threading, tkinter as tk, io, json, requests
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO

# Config
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
def get_backend_url():
    try:
        data = requests.get(CONFIG_URL, timeout=5).json()
        return data.get("backend_url","").rstrip("/")
    except:
        return input("Backend URL:")

BACKEND = get_backend_url()
SAMPLE_RATE, CHANNELS = 44100,1

class Recorder:
    def __init__(self):
        self.recording=False; self.frames=[]
    def start(self):
        self.frames=[]; self.recording=True
        def cb(indata,_,__,__e): 
            if self.recording: self.frames.append(indata.copy())
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE,channels=CHANNELS,callback=cb)
        self.stream.start()
    def stop(self):
        self.recording=False; self.stream.stop(); self.stream.close()
        return np.concatenate(self.frames,0) if self.frames else None

def encode_wav(data):
    raw = (np.int16(np.clip(data,-1,1)*32767)).tobytes()
    buf = io.BytesIO()
    wf = wave.open(buf,'wb')
    wf.setnchannels(CHANNELS); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
    wf.writeframes(raw); wf.close()
    return buf.getvalue()

class App:
    def __init__(self, root):
        self.root=root; root.title("Rolefy – Student")
        # UI fields...
        tk.Label(root,text="Buyer:").grid(row=0,column=0)
        self.ebuyer=tk.Entry(root); self.ebuyer.grid(row=0,column=1)
        tk.Label(root,text="Seller:").grid(row=1,column=0)
        self.eseller=tk.Entry(root); self.eseller.grid(row=1,column=1)
        self.bt1=tk.Button(root,text="Start",command=self.start); self.bt1.grid(row=2,column=0)
        self.bt2=tk.Button(root,text="Stop", command=self.stop, state='disabled'); self.bt2.grid(row=2,column=1)
        tk.Label(root,text="Items:").grid(row=3,column=0)
        self.tp=tk.Text(root,height=4,width=30); self.tp.grid(row=3,column=1)
        tk.Label(root,text="Costs:").grid(row=4,column=0)
        self.tc=tk.Text(root,height=2,width=30); self.tc.grid(row=4,column=1)
        self.bt3=tk.Button(root,text="Submit",command=self.submit,state='disabled'); self.bt3.grid(row=5,column=0,columnspan=2)
        self.lbl=tk.Label(root,text=""); self.lbl.grid(row=6,column=0,columnspan=2)
        self.rec=Recorder(); self.data=None

    def start(self):
        if not self.ebuyer.get().strip() or not self.eseller.get().strip():
            return messagebox.showwarning("","Enter names")
        self.bt1['state']='disabled'; self.bt2['state']='normal'; self.lbl['text']="Recording..."
        threading.Thread(target=self.rec.start, daemon=True).start()

    def stop(self):
        d=self.rec.stop()
        if d is None: return messagebox.showwarning("","No audio")
        self.data=d; self.lbl['text']="Stopped"; self.bt3['state']='normal'; self.bt2['state']='disabled'

    def submit(self):
        items=[i.strip() for i in self.tp.get("1.0","end").split(",") if i.strip()]
        costs=[float(c) for c in self.tc.get("1.0","end").split(",") if c.strip()]
        if len(items)!=len(costs):
            return messagebox.showwarning("","Mismatch")
        wav=encode_wav(self.data)
        files={"audio":("r.wav",wav,"audio/wav")}
        data={"comprador":self.ebuyer.get(),"vendedor":self.eseller.get(),
              "productos":json.dumps(items),"costes":json.dumps(costs)}
        try:
            r=requests.post(BACKEND+"/upload",data=data,files=files,timeout=30)
            if r.status_code==200 and r.json().get("status")=="ok":
                self.show_receipt(items,costs)
                self.reset()
            else: raise Exception(r.text)
        except Exception as e:
            messagebox.showerror("Error",str(e))

    def show_receipt(self, items, costs):
        total=sum(costs)
        # Generar imagen
        w,h=400, 30+20*(len(items)+3)
        img=Image.new("RGB",(w,h),"white"); draw=ImageDraw.Draw(img)
        font=ImageFont.load_default()
        y=10
        draw.text((10,y),f"Rolefy Receipt",font=font); y+=20
        draw.text((10,y),f"Buyer: {self.ebuyer.get()}, Seller: {self.eseller.get()}",font=font); y+=20
        for itm,c in zip(items,costs):
            draw.text((10,y),f"{itm}: €{c:.2f}",font=font); y+=20
        draw.text((10,y),f"Total: €{total:.2f}",font=font)
        # Mostrar y guardar
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG","*.png")])
        if path:
            img.save(path)
            messagebox.showinfo("Saved",f"Receipt saved to {path}")

    def reset(self):
        self.data=None; self.bt3['state']='disabled'; self.bt1['state']='normal'
        self.tp.delete("1.0","end"); self.tc.delete("1.0","end"); self.lbl['text']="Submitted!"

if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
