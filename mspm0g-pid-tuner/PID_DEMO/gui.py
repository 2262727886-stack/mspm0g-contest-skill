#!/usr/bin/env python3
"""MSPM0G3507 PID 调参工具 — 中文 GUI"""

import sys, os, json, threading, queue, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from PID_DEMO.config import load_config, DEFAULT_CONFIG

# ═══ 设计系统 ═══
C = {
    "bg":"#eef2f6","card":"#ffffff","card2":"#f8fafc","hover":"#e6edf5","border":"#d8e0ea",
    "text":"#111827","sub":"#526070","muted":"#94a3b8","plot":"#fbfdff",
    "accent":"#0f766e","accent2":"#1d4ed8","green":"#059669","red":"#dc2626",
    "amber":"#d97706","blue":"#2563eb","pink":"#be185d","logbg":"#0f172a","logfg":"#dbeafe"
}
F = {"b":("Microsoft YaHei UI",10),"m":("Consolas",10),"h":("Microsoft YaHei UI",12,"bold"),
     "big":("Consolas",24,"bold"),"s":("Microsoft YaHei UI",9),"title":("Microsoft YaHei UI",15,"bold"),
     "xl":("Consolas",30,"bold")}

class RoundedButton(tk.Canvas):
    def __init__(self,p,text,command=None,bg=None,fg=None,activebackground=None,activeforeground=None,
                 padx=16,pady=7,font=None,radius=12,cursor="hand2",**kw):
        self._text=text;self._cmd=command;self._bg=bg or C["card"];self._fg=fg or C["text"]
        self._activebg=activebackground or C["hover"];self._activefg=activeforeground or self._fg
        self._font=font or F["b"];self._radius=radius;self._enabled=True
        w=max(82,len(str(text))*14+padx*2);h=34+pady//2
        super().__init__(p,width=w,height=h,bg=p.cget("bg"),highlightthickness=0,bd=0,cursor=cursor,**kw)
        self._draw(False)
        self.bind("<Enter>",lambda e:self._draw(True))
        self.bind("<Leave>",lambda e:self._draw(False))
        self.bind("<Button-1>",self._click)

    def _round_rect(self,x1,y1,x2,y2,r,**kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        return self.create_polygon(pts,smooth=True,**kw)

    def _draw(self,hover=False):
        self.delete("all")
        fill=self._activebg if hover and self._enabled else self._bg
        fg=self._activefg if hover and self._enabled else self._fg
        outline="#cbd5e1" if fill in (C["card"],C["card2"],C["bg"]) else fill
        self._round_rect(1,1,int(self["width"])-1,int(self["height"])-1,self._radius,fill=fill,outline=outline,width=1)
        self.create_text(int(self["width"])//2,int(self["height"])//2,text=self._text,font=self._font,fill=fg)

    def _click(self,_event):
        if self._enabled and self._cmd:self._cmd()

    def config(self,cnf=None,**kw):
        if cnf:kw.update(cnf)
        if "text" in kw:
            self._text=kw.pop("text")
            self["width"]=max(82,len(str(self._text))*14+24)
        if "bg" in kw:self._bg=kw.pop("bg")
        if "fg" in kw:self._fg=kw.pop("fg")
        if "activebackground" in kw:self._activebg=kw.pop("activebackground")
        if "activeforeground" in kw:self._activefg=kw.pop("activeforeground")
        if "state" in kw:self._enabled=(kw.pop("state") != tk.DISABLED)
        if kw:super().config(**kw)
        self._draw(False)
    configure=config

    def cget(self,key):
        if key=="text":return self._text
        if key=="bg":return self._bg
        if key=="fg":return self._fg
        return super().cget(key)

def _card(p,**kw):
    return tk.Frame(p,bg=C["card"],highlightbackground=C["border"],highlightthickness=1,padx=14,pady=12,**kw)
def _btn(p,text,cmd,pri=False):
    bg=C["accent"] if pri else C["card"];fg="white" if pri else C["text"]
    return RoundedButton(p,text=f" {text} ",command=cmd,font=("Microsoft YaHei UI",10),bg=bg,fg=fg,
                         activebackground="#0d9488" if pri else C["hover"],
                         activeforeground="white" if pri else C["text"])
def _lbl(p,text,font=None,fg=None,**kw):
    return tk.Label(p,text=text,font=font or F["b"],fg=fg or C["text"],bg=p.cget("bg"),**kw)
def _ent(p,default,w=8):
    e=tk.Entry(p,font=F["b"],fg=C["text"],bg=C["bg"],relief=tk.FLAT,width=w,
               highlightbackground=C["border"],highlightthickness=1,insertbackground=C["accent"])
    e.insert(0,str(default));e.pack(ipady=3);return e
def _log_widget(p):
    return scrolledtext.ScrolledText(p,font=F["m"],bg=C["logbg"],fg=C["logfg"],
                                     insertbackground=C["logfg"],relief=tk.FLAT,
                                     padx=12,pady=8,wrap=tk.WORD)
def _section_label(p,title,sub=None):
    row=tk.Frame(p,bg=p.cget("bg"));row.pack(fill=tk.X,pady=(0,8))
    _lbl(row,title,F["b"],C["text"]).pack(side=tk.LEFT)
    if sub:_lbl(row,sub,F["s"],C["sub"]).pack(side=tk.RIGHT)
    return row

# ═══ 实时曲线 ═══
class Curve(tk.Canvas):
    def __init__(self,p,h=240):
        super().__init__(p,height=h,bg=C["plot"],highlightthickness=1,highlightbackground=C["border"],bd=0)
        self.H=h;self.data=[];self.target=60;self.max_pts=200;self.max_y=120
        self.bind("<Configure>",lambda e:self.draw())
    def add(self,v,t=None):
        if t is not None:self.target=t
        self.data.append(v)
        if len(self.data)>self.max_pts:self.data.pop(0)
        self.draw()
    def _axes(self,w,h,min_y,max_y):
        M=56;R=20;B=30  # margins: left, right, bottom (增加边距)
        pw=w-M-R;ph=h-B-20
        if pw<10:return M,R,B,pw,ph
        n_ticks=4
        for i in range(n_ticks+1):
            val=min_y+(max_y-min_y)*i/n_ticks
            y=B+ph-ph*i/n_ticks
            self.create_line(M,y,w-R,y,fill="#e8eef5",dash=(2,4) if i>0 else None,width=1)
            self.create_text(M-6,y,text=f"{val:.0f}",font=("Consolas",8),fill=C["sub"],anchor=tk.E)
        if min_y < 0 < max_y:
            zy=B+ph-ph*(0-min_y)/(max_y-min_y)
            self.create_line(M,zy,w-R,zy,fill="#cbd5e1",width=1.2)
        self.create_line(M,B,w-R,B,fill=C["border"])
        self.create_text(w//2,B+16,text="采样点",font=F["s"],fill=C["sub"],anchor=tk.N)
        self.create_text(12,h//2,text="速度",font=F["s"],fill=C["sub"],anchor=tk.S,angle=90)
        return M,R,B,pw,ph
    def draw(self):
        self.delete("all");w=self.winfo_width();h=self.H
        if w<10:return
        vals=self.data+[self.target]
        min_y=min(0,min(vals) if vals else 0)
        max_y=max(self.max_y,max(vals) if vals else self.max_y)
        if max_y-min_y<10:max_y=min_y+10
        M,R,B,pw,ph=self._axes(w,h,min_y,max_y)
        n=len(self.data)
        if n<2 or ph<1:return
        def ymap(v):
            v=max(min_y,min(max_y,v))
            return B+ph-ph*(v-min_y)/(max_y-min_y)
        ty=ymap(self.target)
        self.create_line(M,ty,w-R,ty,fill=C["red"],dash=(6,3),width=1.5,tags="curve")
        self.create_text(w-R,ty-8,text=f"目标={self.target:.0f}",font=("Consolas",8),fill=C["red"],anchor=tk.E,tags="curve")
        pts=[]
        for i in range(n):
            x=M+pw*i/max(1,n-1);y=ymap(self.data[i])
            pts.extend([x,y])
        if len(pts)>=4:
            for i in range(0,len(pts)-2,2):
                self.create_line(pts[i],pts[i+1],pts[i+2],pts[i+3],fill=C["accent"],width=1.8,tags="curve")
        # last value
        if pts:
            lx=pts[-2];ly=pts[-1]
            self.create_oval(lx-4,ly-4,lx+4,ly+4,fill=C["accent"],outline="white",width=2,tags="curve")
            # 确保速度值在可见区域内
            text_x = lx + 10
            text_anchor = tk.W
            if text_x > w - R - 50:  # 如果太靠右，改为左对齐
                text_x = lx - 10
                text_anchor = tk.E
            self.create_text(text_x, ly-8, text=f"{self.data[-1]:.1f}", font=("Consolas",9,"bold"), fill=C["accent"], anchor=text_anchor, tags="curve")
        self.create_rectangle(M+6,6,M+126,24,fill=C["card"],outline=C["border"],tags="curve")
        self.create_line(M+12,14,M+28,14,fill=C["accent"],width=2,tags="curve")
        self.create_text(M+44,14,text="速度",font=F["s"],fill=C["text"],anchor=tk.W,tags="curve")
        self.create_line(M+82,14,M+92,14,fill=C["red"],dash=(4,2),tags="curve")
        self.create_text(M+106,14,text="目标",font=F["s"],fill=C["red"],anchor=tk.W,tags="curve")
    def clear(self):self.data.clear();self.delete("all");self._axes(self.winfo_width(),self.H,0,self.max_y)

# ═══ 主应用 ═══
class App:
    def __init__(self,root):
        self.root=root;self.root.title("MSPM0G3507 PID 调参工具 v0.4")
        self.root.geometry("1180x760");self.root.minsize(980,620)
        self.root.configure(bg=C["bg"])
        self._style_ttk()
        # 优先从 exe 同目录加载 config.json (PyInstaller 打包后 cwd 可能不对)
        self._cfg_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json")
        if not os.path.exists(self._cfg_path):
            self._cfg_path = "config.json"
        self.config = load_config(self._cfg_path)
        # 启动诊断
        _llm_ok = self.config.get("LLM_API_KEY","") not in ("","sk-your-key-here")
        _url = self.config.get("LLM_API_BASE_URL","")
        _model = self.config.get("LLM_MODEL_NAME","")
        print(f"[CONFIG] path={self._cfg_path} exists={os.path.exists(self._cfg_path)}")
        print(f"[LLM] key={'SET' if _llm_ok else 'MISSING'} url={_url} model={_model}")
        self.running=False;self._stop_event=threading.Event();self.q=queue.Queue();self.pid={"p":5.0,"i":2.0,"d":0.0}
        self._bridge=None;self._conn=False;self.mode="auto"
        self._top_bar()
        self._layout()
        self._show_page("auto")
        self._poll()

    def _style_ttk(self):
        style=ttk.Style()
        try:style.theme_use("clam")
        except:pass
        style.configure("TCombobox",fieldbackground=C["card2"],background=C["card2"],
                        foreground=C["text"],arrowcolor=C["accent"],padding=3)

    # ═══ 顶部串口栏 ═══
    def _top_bar(self):
        b=tk.Frame(self.root,bg=C["card"],height=58,highlightbackground=C["border"],highlightthickness=0)
        b.pack(fill=tk.X);b.pack_propagate(False)
        title=tk.Frame(b,bg=C["card"]);title.pack(side=tk.LEFT,padx=16,pady=8)
        _lbl(title,"MSPM0G3507 PID 调参",F["title"],C["accent"]).pack(anchor=tk.W)
        _lbl(title,"串口采样 / 自动整定 / 稳定性评估",F["s"],C["sub"]).pack(anchor=tk.W)
        _lbl(b,"端口",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(26,4),pady=20)
        self._tb_port=ttk.Combobox(b,values=self._scan_ports(),width=9,font=F["b"])
        self._tb_port.set(self.config.get("SERIAL_PORT","AUTO"))
        self._tb_port.pack(side=tk.LEFT,ipady=1,pady=14)
        _btn(b,"刷新",lambda:self._tb_port.config(values=self._scan_ports())).pack(side=tk.LEFT,padx=(4,10),pady=12)
        _lbl(b,"波特率",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(0,4),pady=20)
        self._tb_baud=_ent(b,str(self.config.get("BAUD_RATE",115200)),6)
        self._tb_baud.pack(side=tk.LEFT,ipady=2,pady=14)
        self._tb_cbtn=tk.Button(b,text="连接设备",font=F["b"],bg=C["accent"],fg="white",
                                activebackground="#4338ca",activeforeground="white",
                                relief=tk.FLAT,bd=0,padx=12,pady=4,cursor="hand2",command=self._conn_toggle)
        self._tb_cbtn.pack(side=tk.LEFT,padx=12,pady=12)
        self._tb_dot=tk.Label(b,text="●",font=("Consolas",9),fg=C["muted"],bg=C["card"])
        self._tb_dot.pack(side=tk.RIGHT,padx=(0,4),pady=19)
        self._tb_lbl=_lbl(b,"离线",F["s"],C["muted"])
        self._tb_lbl.pack(side=tk.RIGHT,padx=(0,16),pady=20)

    @staticmethod
    def _scan_ports():
        try:
            import serial.tools.list_ports
            ports=[p.device for p in serial.tools.list_ports.comports()]
            return ports if ports else ["AUTO","COM1","COM2","COM3","COM4","COM5","COM6"]
        except:return ["AUTO","COM1","COM2","COM3","COM4","COM5","COM6"]

    def _conn_toggle(self):
        if not self._conn:
            from PID_DEMO.bridge import SerialBridge
            try:baud=int(self._tb_baud.get())
            except:baud=115200
            port=self._tb_port.get().strip() or "AUTO"
            self._bridge=SerialBridge(port=port,baud=baud)
            if self._bridge.connect():
                self._conn=True
                self._tb_cbtn.config(text="● 已连接 — 点此断开",bg="#dcfce7",fg=C["green"],activebackground="#bbf7d0")
                self._tb_dot.config(fg=C["green"],font=("Consolas",14));self._tb_lbl.config(text="设备在线",fg=C["green"],font=F["b"])
            else:self._tb_dot.config(fg=C["red"])
        else:
            self._bridge.disconnect();self._conn=False
            self._tb_cbtn.config(text="连接设备",bg=C["accent"],fg="white",activebackground="#4338ca")
            self._tb_dot.config(fg=C["muted"]);self._tb_lbl.config(text="离线",fg=C["muted"])

    # ═══ 三栏布局 ═══
    def _layout(self):
        main=tk.Frame(self.root,bg=C["bg"]);main.pack(fill=tk.BOTH,expand=True)

        # ── 左侧: 设置选项 ──
        self._left=tk.Frame(main,bg=C["card"],width=174,highlightbackground=C["border"],highlightthickness=0)
        self._left.pack(side=tk.LEFT,fill=tk.Y);self._left.pack_propagate(False)
        tk.Frame(self._left,bg=C["border"],height=1).pack(fill=tk.X,padx=10)

        _lbl(self._left,"工作区",F["h"],C["text"]).pack(anchor=tk.W,padx=16,pady=(16,8))
        self._nav={}
        for mode,label in [("auto","自动调参"),("manual","手动配置"),("sim_cfg","仿真设置"),("settings","LLM 设置")]:
            b=tk.Button(self._left,text=label,font=F["b"],fg=C["sub"],bg=C["card"],
                        activebackground="#dff6f1",activeforeground=C["accent"],
                        relief=tk.FLAT,bd=0,padx=16,pady=11,cursor="hand2",
                        anchor=tk.W,command=lambda m=mode:self._show_page(m))
            b.pack(fill=tk.X)
            self._nav[mode]=b
        tk.Frame(self._left,bg=C["border"],height=1).pack(fill=tk.X,padx=10,pady=8)

        _lbl(self._left,"连接设置",F["s"],C["muted"]).pack(anchor=tk.W,padx=16,pady=(4,4))
        _lbl(self._left,"端口号和波特率在顶部栏修改",F["s"],C["muted"],wraplength=136,justify=tk.LEFT).pack(anchor=tk.W,padx=16)

        tk.Frame(self._left,bg=C["border"],height=1).pack(fill=tk.X,padx=10,pady=(16,4))
        _lbl(self._left,"v0.4",F["s"],C["muted"]).pack(side=tk.BOTTOM,anchor=tk.W,padx=16,pady=10)

        # ── 中间: 设置内容 ──
        self._center=tk.Frame(main,bg=C["bg"])

        # ── 右侧: PID 曲线 ──
        self._right=tk.Frame(main,bg=C["bg"],width=380)
        self._right.pack(side=tk.RIGHT,fill=tk.BOTH);self._right.pack_propagate(False)

        # 曲线卡片
        cf=_card(self._right);cf.pack(fill=tk.BOTH,expand=True,padx=(6,12),pady=(12,6))
        _section_label(cf,"实时曲线","速度 / 目标")
        self._curve=Curve(cf,280)
        self._curve.pack(fill=tk.BOTH,expand=True,pady=(4,0))

        sc=_card(self._right);sc.pack(fill=tk.X,padx=(6,12),pady=(0,6))
        _lbl(sc,"稳定性评分",F["s"],C["sub"]).pack(anchor=tk.W)
        self._score_var=tk.StringVar(value="--- %")
        tk.Label(sc,textvariable=self._score_var,font=F["xl"],fg=C["accent"],bg=C["card"]).pack(anchor=tk.W)

        rc=_card(self._right);rc.pack(fill=tk.X,padx=(6,12),pady=(0,12))
        _lbl(rc,"推荐 PID",F["s"],C["sub"]).pack(anchor=tk.W)
        self._rec_var=tk.StringVar(value="---")
        tk.Label(rc,textvariable=self._rec_var,font=F["big"],fg=C["green"],bg=C["card"]).pack(anchor=tk.W)

        # 构建各页
        self._pages={}
        self._build_auto();self._build_manual();self._build_sim_cfg();self._build_settings()

    def _show_page(self,mode):
        self.mode=mode
        for m,b in self._nav.items():
            sel=(m==mode)
            b.config(bg="#dff6f1" if sel else C["card"],fg=C["accent"] if sel else C["sub"])
        for p in self._pages.values():p.pack_forget()
        self._center.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        self._pages[mode].pack(fill=tk.BOTH,expand=True,padx=(8,0),pady=(12,12))

    # ═══ 自动调参页面 ═══
    def _build_auto(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["auto"]=pg

        bar=_card(pg);bar.pack(fill=tk.X,pady=(0,10))
        # 第一行: 模式 + 算法 + 按钮
        r1=tk.Frame(bar,bg=C["card"]);r1.pack(fill=tk.X,pady=(0,4))
        self._auto_mode=tk.StringVar(value="sim")
        _lbl(r1,"模式:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        for mode,label in [("sim","仿真"),("hw","硬件")]:
            tk.Radiobutton(r1,text=label,variable=self._auto_mode,value=mode,font=F["b"],
                          bg=C["card"],fg=C["text"],activebackground=C["card"],
                          selectcolor=C["card"],cursor="hand2",
                          command=lambda m=mode:self._mode_changed(m)).pack(side=tk.LEFT,padx=(0,8))
        tk.Frame(r1,bg=C["border"],width=1).pack(side=tk.LEFT,fill=tk.Y,padx=6)
        self._auto_algo=ttk.Combobox(r1,values=["LLM 大模型","引导调参 P→I→D","贝叶斯优化","Ziegler-Nichols","继电反馈法"],state="readonly",width=14,font=F["b"])
        self._auto_algo.set("LLM 大模型");self._auto_algo.pack(side=tk.LEFT,padx=(4,8))
        self._auto_btn=_btn(r1,"开始调参",self._auto_start,pri=True)
        self._auto_btn.pack(side=tk.RIGHT)
        self._auto_mode_lbl=_lbl(r1,"",F["s"],C["muted"])
        self._auto_mode_lbl.pack(side=tk.RIGHT,padx=(0,10))
        # 第二行: 轮次 + 目标 + 秒/轮
        r2=tk.Frame(bar,bg=C["card"]);r2.pack(fill=tk.X)
        _lbl(r2,"轮次:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        self._auto_rnd=_ent(r2,15,4);self._auto_rnd.pack(side=tk.LEFT,padx=(0,12))
        _lbl(r2,"目标:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        self._auto_tgt=_ent(r2,60,4);self._auto_tgt.pack(side=tk.LEFT,padx=(0,12))
        _lbl(r2,"秒/轮:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        self._auto_sec=_ent(r2,5,3);self._auto_sec.pack(side=tk.LEFT)

        # PID 卡片
        cd=tk.Frame(pg,bg=C["bg"]);cd.pack(fill=tk.X,pady=(0,10))
        self._av={}
        for lab,key,clr in [("Kp 比例","p",C["blue"]),("Ki 积分","i",C["red"]),("Kd 微分","d",C["amber"])]:
            c=_card(cd);c.pack(side=tk.LEFT,padx=(0,8),fill=tk.X,expand=True)
            _lbl(c,lab,F["s"],C["sub"]).pack(anchor=tk.W)
            v=tk.StringVar(value="---")
            tk.Label(c,textvariable=v,font=F["big"],fg=clr,bg=C["card"]).pack(anchor=tk.W,pady=(1,0))
            self._av[key]=v

        lf=_card(pg);lf.pack(fill=tk.BOTH,expand=True)
        _section_label(lf,"决策日志","批量刷新，避免串口采样卡顿")
        self._auto_log=_log_widget(lf)
        self._auto_log.pack(fill=tk.BOTH,expand=True,pady=(4,0))

    def _mode_changed(self,mode):
        if mode=="hw":
            self._auto_mode_lbl.config(text="需连接设备",fg=C["red"])
        else:
            self._auto_mode_lbl.config(text="仿真模式",fg=C["muted"])

    def _auto_start(self):
        if self.running:
            self._stop_event.set();return
        self._stop_event.clear();self.running=True;algo=self._auto_algo.get()
        try:mr=int(self._auto_rnd.get())
        except:mr=15
        try:tgt=int(self._auto_tgt.get())
        except:tgt=60
        try:sec_per_round=float(self._auto_sec.get())
        except:sec_per_round=5.0
        self._auto_log.delete(1.0,tk.END);self._curve.clear();self.q.put(("target",tgt))
        self._auto_log_msg(f"[自动调参] 算法: {algo} | 轮次: {mr} | 目标: {tgt} | {sec_per_round:.0f}秒/轮")
        if hasattr(self,'_auto_btn'):
            self._auto_btn.config(text=" 停止 ",bg=C["red"],fg="white")
        threading.Thread(target=self._auto_worker,args=(algo,mr,tgt,sec_per_round),daemon=True).start()

    def _auto_worker(self,algo,mr,tgt,sec_per_round=10.0):
        """统一调参引擎: 硬件优先, 未连接则仿真"""
        try:
            self._auto_worker_inner(algo,mr,tgt,sec_per_round)
        except Exception as e:
            import traceback
            self._auto_log_msg(f"[致命错误] {e}")
            self._auto_log_msg(traceback.format_exc()[-300:])
            self.q.put(("done",None))

    def _auto_worker_inner(self,algo,mr,tgt,sec_per_round=10.0):
        # 引导调参走独立流程
        if algo == "引导调参 P→I→D":
            use_hw = (self._auto_mode.get() == "hw")
            self._guided_worker(tgt, sec_per_round, use_hw)
            return

        from PID_DEMO.sim_adapter import SimAdapter
        from PID_DEMO.engine import run_tuning_engine
        from PID_DEMO.buffer import SpeedBuffer
        import time

        # 判断模式
        want_hw=(self._auto_mode.get()=="hw")
        if want_hw:
            from PID_DEMO.bridge import SerialBridge
            port=self._tb_port.get().strip() or "AUTO"
            try: baud=int(self._tb_baud.get())
            except: baud=115200
            bridge=SerialBridge(port=port,baud=baud)
            if not bridge.connect():
                self._auto_log_msg("[错误] 无法打开串口, 检查是否被其他程序占用")
                self.q.put(("done",None));return
            using_hw=True
            self._auto_log_msg("[硬件模式] 串口调参")
            bridge.flush()
            self._auto_log_msg(f"[TARGET] send L:{tgt} R:{tgt}")
            if not bridge.set_target_checked(tgt,tgt,timeout_s=3.0):
                raw = " | ".join(getattr(bridge, "last_probe_lines", [])[-5:])
                bridge.disconnect()
                self._auto_log_msg("[ERROR] MCU target echo mismatch. Flash latest pid_tuner_car firmware first.")
                if raw:
                    self._auto_log_msg(f"[RX] {raw}")
                else:
                    self._auto_log_msg("[RX] no response after TARGET/STATUS")
                self.q.put(("done",None));return
            bridge.flush()
            self._auto_log_msg("[检测] 等待数据...")
            samples=bridge.read_samples(5,timeout_s=6.0)
            if len(samples)<2:
                bridge.disconnect()
                self._auto_log_msg("[错误] 未收到 MCU 数据")
                self.q.put(("done",None));return
            self._auto_log_msg(f"[检测] 收到 {len(samples)} 点数据, 开始调参")
        else:
            motor_params = self.config.get("SIM_MOTOR_PARAMS", None)
            bridge=SimAdapter(kp=2.0,ki=0.0,target=tgt,motor_params=motor_params); using_hw=False
            self._auto_log_msg("[仿真模式] 本地模型")

        # ── 预热: P-only 扫频找起点 ──
        self._auto_log_msg("[预热] P-only 扫频...")
        best_p={"p":3.0,"i":0.0,"d":0.0};best_err=999
        for test_kp in [3.0,6.0,10.0]:
            if self._stop_event.is_set():self._auto_log_msg("[已停止]");self.q.put(("done",None));return
            if using_hw:
                bridge.set_target(tgt,tgt)
                bridge.set_pid(test_kp,0,0)
                time.sleep(0.12)
                bridge.flush()
            else: bridge.sim.set_pid(test_kp,0,0)
            buf=SpeedBuffer(60)
            for sample_idx in range(60):
                if self._stop_event.is_set():self._auto_log_msg("[已停止]");self.q.put(("done",None));return
                s=bridge.read_sample()
                if s:
                    buf.add(s)
                    if sample_idx % 4 == 0:
                        self.q.put(("curve",s.get("speed_L",0)))
            m=buf.calculate_metrics()
            last_s=buf._data[-1] if len(buf)>0 else {}
            cur_v=(last_s.get("speed_L",0)+last_s.get("speed_R",0))/2
            self.q.put(("curve",cur_v))
            self._auto_log_msg(f"  预热 P={test_kp:.1f}: speed={cur_v:.0f} tgt={m.get('avg_target',tgt):.0f} err={m['avg_error']:.1f} [{m.get("status_cn", m["status"])}]")
            if m["avg_error"]<best_err:best_err=m["avg_error"];best_p={"p":test_kp,"i":0.0,"d":0.0}
        # 最佳 P 加初始 I
        best_p["i"]=best_p["p"]*0.3
        self.q.put(("pid",best_p))
        self._auto_log_msg(f"[预热完成] 起点: P={best_p['p']:.1f} I={best_p['i']:.1f}")

        if self._stop_event.is_set():self._auto_log_msg("[已停止]");self.q.put(("done",None));return

        # ── 主调参循环 ──
        if not using_hw:
            bridge=SimAdapter(kp=best_p["p"],ki=best_p["i"],target=tgt)
        else:
            bridge.set_pid(best_p["p"],best_p["i"])
        try:
            last_curve_push=[0.0]
            def push_curve_throttled(sample):
                now_t=time.monotonic()
                if now_t-last_curve_push[0]>=0.05:
                    last_curve_push[0]=now_t
                    self.q.put(("curve",sample.get("speed_L",0)))
            # 根据秒/轮计算 buffer_size (50 samples/sec)
            engine_config = dict(self.config)
            engine_config["BUFFER_SIZE"] = int(sec_per_round * 50)
            final=run_tuning_engine(
                bridge=bridge,config=engine_config,current_pid=best_p,
                on_sample=push_curve_throttled,
                on_round_complete=lambda r,pid,m,res:(
                    self.q.put(("pid",pid)),
                    self.q.put(("curve",m.get("avg_speed",0))),
                    self.q.put(("score",f"{max(0,100-m['avg_error']*2-m['overshoot']*0.3):.0f}%")),
                    self.q.put(("rec",f"P={pid['p']:.3f} I={pid['i']:.3f}")),
                    self._auto_log_msg(f"R{r}: speed={m.get('avg_speed',0):.0f} tgt={m.get('avg_target',tgt):.0f} err={m['avg_error']:.1f} [{m.get("status_cn", m["status"])}] P={pid['p']:.3f} I={pid['i']:.3f}"),
                    (res and res.get("analysis_summary","")) and self._auto_log_msg(f"  LLM: {res.get('analysis_summary','')}")
                ),
                abort_check=lambda:self._stop_event.is_set()
            )
            if using_hw:
                try: bridge.disconnect()
                except: pass
            self._auto_log_msg(f"[完成] 最优: P={final['p']:.3f} I={final['i']:.3f}")
        except Exception as e:
            self._auto_log_msg(f"[异常] {e}")
        finally:
            self.q.put(("done",None))

    # ═══ 引导调参 P→I→D ═══
    def _guided_worker(self, tgt, sec_per_round=10.0, use_hw=False):
        from PID_DEMO.sim_adapter import SimAdapter
        from PID_DEMO.buffer import SpeedBuffer
        import time

        motor_params = self.config.get("SIM_MOTOR_PARAMS", None)
        steps_per_round = int(sec_per_round * 50)  # 50 samples/sec

        # 硬件模式: 连接串口
        hw_bridge = None
        if use_hw:
            from PID_DEMO.bridge import SerialBridge
            port = self._tb_port.get().strip() or "AUTO"
            try: baud = int(self._tb_baud.get())
            except: baud = 115200
            hw_bridge = SerialBridge(port=port, baud=baud)
            if not hw_bridge.connect():
                self._auto_log_msg("[错误] 无法打开串口")
                self.q.put(("done", None)); return
            hw_bridge.set_target(tgt, tgt)
            hw_bridge.flush()
            self._auto_log_msg(f"[硬件模式] 串口 {port} @ {baud}")
            # 验证数据
            samples = hw_bridge.read_samples(5, timeout_s=6.0)
            if len(samples) < 2:
                self._auto_log_msg("[错误] 未收到 MCU 数据")
                hw_bridge.disconnect()
                self.q.put(("done", None)); return
            self._auto_log_msg(f"[检测] 收到 {len(samples)} 点, 开始调参")

        def make_bridge(p, i):
            """创建 bridge: 硬件用共享串口, 仿真每次新建"""
            if use_hw:
                hw_bridge.set_pid(p, i, 0)
                return hw_bridge
            else:
                return SimAdapter(kp=p, ki=i, target=tgt, motor_params=motor_params)

        def collect(bridge, p, i, d, steps=None, warmup_ratio=0.3):
            """采集数据, 返回 {steady: 稳态指标, full: 全程指标}"""
            if steps is None: steps = steps_per_round
            bridge.set_pid(p, i, d)
            all_samples = []
            for idx in range(steps):
                if self._stop_event.is_set(): return None
                s = bridge.read_sample()
                if s:
                    all_samples.append(s)
                    if idx % 5 == 0:
                        self.q.put(("curve", s.get("speed_L", 0)))
                if not use_hw:
                    time.sleep(0.005)  # 仿真需要延时, 硬件不需要
            if not all_samples: return None
            # 全程指标 (含瞬态超调)
            full_buf = SpeedBuffer(len(all_samples))
            for s in all_samples: full_buf.add(s)
            full_m = full_buf.calculate_metrics()
            # 稳态指标 (跳过瞬态)
            warmup_n = int(len(all_samples) * warmup_ratio)
            steady_samples = all_samples[warmup_n:]
            if len(steady_samples) < 10:
                steady_samples = all_samples
            steady_buf = SpeedBuffer(len(steady_samples))
            for s in steady_samples: steady_buf.add(s)
            steady_m = steady_buf.calculate_metrics()
            return {"steady": steady_m, "full": full_m}

        self._auto_log_msg("═" * 50)
        self._auto_log_msg("【引导调参】先调 P → 再加 I → 最后加 D")
        self._auto_log_msg(f"目标速度: {tgt} 脉冲/20ms")
        self._auto_log_msg("═" * 50)

        # ── 评分函数 ──
        def score_pi(result):
            """评分: 到达target > 稳态有效值 > 波动小 > 瞬态超调少"""
            sm = result["steady"]   # 稳态指标
            fm = result["full"]     # 全程指标 (含瞬态)
            ratio = sm.get("speed_ratio", 0)
            fluc = sm.get("fluctuation", 99)
            vr = sm.get("valid_ratio", 0)
            full_over = fm.get("overshoot", 0)  # 瞬态超调
            # 到不了 target 直接淘汰
            if ratio < 0.90: return -100 + ratio * 10
            # 有效值多 + 波动小 + 瞬态超调少
            return vr * 50 - fluc * 5 - full_over * 0.5

        def score_d(result):
            sm = result["steady"]
            fm = result["full"]
            return -fm["overshoot"] * 3 - sm["avg_error"] * 2

        # ── 贝叶斯优化工具 ──
        import math, random as _rnd

        def bayesian_opt(collect_fn, p_i_pairs, score_fn, n_rounds, log_prefix, var_name):
            """贝叶斯优化: 网格初筛 → EI 采样精搜"""
            observations = []  # [(p, i, score, metrics)]

            # 初筛: 网格点
            self._auto_log_msg(f"  初筛 {len(p_i_pairs)} 个候选点...")
            for (tp, ti) in p_i_pairs:
                if self._stop_event.is_set(): return None, None, None
                m = collect_fn(tp, ti)
                if m is None: return None, None, None
                sc = score_fn(m)
                observations.append((tp, ti, sc, m))
                sm = m["steady"]; fm = m["full"]
                tag = " ★" if sc == max(o[2] for o in observations) else ""
                self._auto_log_msg(f"  {var_name}={tp:.1f}/{ti:.1f} → speed={sm['avg_speed']:.0f} 有效={sm['valid_ratio']*100:.0f}% 波动={sm['fluctuation']:.2f} 瞬超={fm['overshoot']:.0f}% 评分={sc:.1f}{tag}")

            # 贝叶斯精搜: 在最佳点附近精细网格搜索
            self._auto_log_msg(f"  精搜 ({n_rounds} 轮, 最佳点附近)...")
            for rnd in range(n_rounds):
                if self._stop_event.is_set(): break
                best_obs = max(observations, key=lambda o: o[2])
                best_sc = best_obs[2]
                bp, bi = best_obs[0], best_obs[1]

                # 在最佳点附近生成精细候选 (每轮范围缩小)
                shrink = 0.6 ** rnd  # 每轮缩小 40%
                p_step = max(0.5, bp * 0.15 * shrink)
                i_step = max(0.1, bi * 0.2 * shrink)
                candidates = []
                for dp in [-p_step, 0, p_step]:
                    for di in [-i_step, 0, i_step]:
                        cp = max(1, round(bp + dp, 1))
                        ci = max(0.1, round(bi + di, 1))
                        if (cp, ci) not in [(o[0], o[1]) for o in observations]:
                            candidates.append((cp, ci))

                if not candidates:
                    self._auto_log_msg(f"  [{rnd+1}] 无新候选点, 跳过")
                    continue

                # 评估所有候选
                for (tp, ti) in candidates:
                    m = collect_fn(tp, ti)
                    if m is None: break
                    sc = score_fn(m)
                    observations.append((tp, ti, sc, m))
                    if sc > best_sc:
                        tag = " ★"
                        best_sc = sc
                    else:
                        tag = ""
                    sm = m["steady"]; fm = m["full"]
                    self._auto_log_msg(f"  [{rnd+1}] {var_name}={tp:.1f}/{ti:.1f} → speed={sm['avg_speed']:.0f} 有效={sm['valid_ratio']*100:.0f}% 波动={sm['fluctuation']:.2f} 瞬超={fm['overshoot']:.0f}% 评分={sc:.1f}{tag}")

            best = max(observations, key=lambda o: o[2])
            return best[0], best[1], best[3]

        # ── 阶段1: P+I 贝叶斯优化 ──
        self._auto_log_msg("")
        self._auto_log_msg("━━ 阶段1: P+I 贝叶斯优化 ━━")
        self._auto_log_msg("网格初筛 → EI 精搜最优 P+I")
        self._auto_log_msg("")

        pi_grid = [(p, i) for p in [3, 5, 8, 10, 15, 20] for i in [0.3, 0.5, 1.0, 1.5, 2.0, 3.0]]
        def collect_pi(p, i):
            bridge = make_bridge(p, i)
            return collect(bridge, p, i, 0)

        best_p, best_i, m1 = bayesian_opt(collect_pi, pi_grid, score_pi, 8, "P+I", "P/I")
        if best_p is None: self._auto_log_msg("[已停止]"); self.q.put(("done",None)); return

        self.q.put(("pid", {"p": best_p, "i": best_i, "d": 0}))
        self._auto_log_msg(f"")
        self._auto_log_msg(f"✓ 阶段1结论: P={best_p:.1f} I={best_i:.1f}")

        # ── 阶段2: D 贝叶斯优化 ──
        self._auto_log_msg("")
        self._auto_log_msg("━━ 阶段2: D 贝叶斯优化 ━━")
        self._auto_log_msg("固定 P+I, 搜索最佳 D")
        self._auto_log_msg("")

        d_grid = [(best_p, best_i)]  # D 用 1D 搜索, P/I 固定
        observations_d = []

        # 初筛 D 候选
        d_candidates = [0.0, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
        for test_d in d_candidates:
            if self._stop_event.is_set(): self._auto_log_msg("[已停止]"); self.q.put(("done",None)); return
            bridge = SimAdapter(kp=best_p, ki=best_i, target=tgt, motor_params=motor_params)
            m = collect(bridge, best_p, best_i, test_d)
            if m is None: self._auto_log_msg("[已停止]"); self.q.put(("done",None)); return
            sc = score_d(m)
            observations_d.append((test_d, sc, m))
            sm = m["steady"]; fm = m["full"]
            tag = " ★" if sc == max(o[1] for o in observations_d) else ""
            self._auto_log_msg(f"  D={test_d:4.1f} → err={sm['avg_error']:.1f} 超调={fm['overshoot']:.1f}% 评分={sc:.1f}{tag}")

        # D 精搜
        self._auto_log_msg(f"  精搜 D (5 轮, 最佳点附近)...")
        for rnd in range(5):
            if self._stop_event.is_set(): break
            best_obs_d = max(observations_d, key=lambda o: o[1])
            best_sc_d = best_obs_d[1]
            bd = best_obs_d[0]

            # 在最佳 D 附近精细搜索 (范围逐轮缩小)
            shrink = 0.6 ** rnd
            d_step = max(0.05, bd * 0.2 * shrink + 0.1 * shrink)
            d_cands = [max(0, round(bd + d, 2)) for d in [-d_step, 0, d_step]]
            d_cands = [d for d in d_cands if d not in [o[0] for o in observations_d]]
            if not d_cands:
                self._auto_log_msg(f"  [{rnd+1}] 无新候选, 跳过")
                continue

            for dc in d_cands:
                bridge = SimAdapter(kp=best_p, ki=best_i, target=tgt, motor_params=motor_params)
                m = collect(bridge, best_p, best_i, dc)
                if m is None: break
                sc = score_d(m)
                observations_d.append((dc, sc, m))
                tag = " ★" if sc > best_sc_d else ""
                sm = m["steady"]; fm = m["full"]
                self._auto_log_msg(f"  [{rnd+1}] D={dc:4.2f} → err={sm['avg_error']:.1f} 超调={fm['overshoot']:.1f}% 评分={sc:.1f}{tag}")
                if sc > best_sc_d: best_sc_d = sc

        best_d = max(observations_d, key=lambda o: o[1])[0]
        self.q.put(("pid", {"p": best_p, "i": best_i, "d": best_d}))
        self._auto_log_msg(f"")
        self._auto_log_msg(f"✓ 阶段2结论: D={best_d:.1f}")

        # ── 最终验证 ──
        self._auto_log_msg("")
        self._auto_log_msg("═" * 50)
        self._auto_log_msg(f"【最终验证】P={best_p:.1f} I={best_i:.1f} D={best_d:.1f}")
        self._auto_log_msg("═" * 50)

        bridge = make_bridge(best_p, best_i)
        result = collect(bridge, best_p, best_i, best_d)
        if result:
            sm = result["steady"]; fm = result["full"]
            self._auto_log_msg(f"  速度: {sm['avg_speed']:.1f} / {tgt}")
            self._auto_log_msg(f"  有效值: {sm['valid_ratio']*100:.0f}% (target±0.3)")
            self._auto_log_msg(f"  稳态波动: {sm['fluctuation']:.2f}")
            self._auto_log_msg(f"  瞬态超调: {fm['overshoot']:.1f}%")
            self._auto_log_msg(f"  稳态误差: {sm['steady_state_error']:.1f}")
            score = max(0, 100 - sm['avg_error']*2 - fm['overshoot']*0.3)
            self.q.put(("score", f"{score:.0f}%"))
            self.q.put(("rec", f"P={best_p:.1f} I={best_i:.1f} D={best_d:.1f}"))

        # 清理硬件连接
        if use_hw and hw_bridge:
            try: hw_bridge.disconnect()
            except: pass

        self._auto_log_msg("")
        self._auto_log_msg("✅ 引导调参完成!")
        self.q.put(("done", None))

    def _auto_log_msg(self,msg):self.q.put(("auto_log",msg))

    # ═══ 手动配置页面 ═══
    def _build_manual(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["manual"]=pg

        bar=_card(pg);bar.pack(fill=tk.X,pady=(0,10))

        # 第一行：模式选择 + 参数输入
        r1=tk.Frame(bar,bg=C["card"]);r1.pack(fill=tk.X,pady=(0,6))

        # 模式选择
        self._manual_mode=tk.StringVar(value="sim")
        _lbl(r1,"模式:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        for mode,label in [("sim","仿真"),("hw","硬件")]:
            tk.Radiobutton(r1,text=label,variable=self._manual_mode,value=mode,font=F["b"],
                          bg=C["card"],fg=C["text"],activebackground=C["card"],
                          selectcolor=C["card"],cursor="hand2").pack(side=tk.LEFT,padx=(0,8))
        tk.Frame(r1,bg=C["border"],width=1).pack(side=tk.LEFT,fill=tk.Y,padx=6)

        # 参数输入
        for lab,attr,defv in [("Kp","_mp",3.0),("Ki","_mi",1.0),("Kd","_md",0.0)]:
            g=tk.Frame(r1,bg=C["card"]);g.pack(side=tk.LEFT,padx=(0,6))
            _lbl(g,lab,F["s"],C["sub"]).pack(anchor=tk.W)
            e=_ent(g,defv,6);setattr(self,attr,e)
        _lbl(r1,"目标:",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(8,2))
        self._mtgt=_ent(r1,60,4);self._mtgt.pack(side=tk.LEFT,padx=(0,8))
        _lbl(r1,"次数:",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(4,2))
        self._mtests=_ent(r1,3,3);self._mtests.pack(side=tk.LEFT,padx=(0,8))
        _lbl(r1,"秒/次:",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(2,2))
        self._msec=_ent(r1,5,3);self._msec.pack(side=tk.LEFT)

        # 第二行：按钮
        r2=tk.Frame(bar,bg=C["card"]);r2.pack(fill=tk.X)
        _btn(r2,"📡 仅观察",self._m_observe,pri=False).pack(side=tk.LEFT,padx=(0,6))
        _btn(r2,"📤 发送PID",self._m_send,pri=True).pack(side=tk.LEFT,padx=(0,6))
        _btn(r2,"▶ 开始测试",self._m_start,pri=True).pack(side=tk.LEFT,padx=(0,6))
        _btn(r2,"📊 模型评估",self._m_model).pack(side=tk.LEFT,padx=(0,6))
        _btn(r2,"🗑 清空曲线",self._m_clear).pack(side=tk.LEFT,padx=(0,6))

        # 日志
        lf=_card(pg);lf.pack(fill=tk.BOTH,expand=True)
        _section_label(lf,"测试日志","手动 PID 测试")
        self._m_log=_log_widget(lf)
        self._m_log.pack(fill=tk.BOTH,expand=True,pady=(4,0))

    def _m_observe(self):
        """仅观察模式：只接收串口数据并显示波形，不发送任何命令"""
        if self.running:
            self._stop_event.set()
            return
        if not self._conn:
            self._m_log_msg("未连接设备")
            return
        self._stop_event.clear()
        self.running = True
        self._curve.clear()
        self._m_log.delete(1.0, tk.END)
        self._m_log_msg("📡 仅观察模式：只显示波形，不发送命令")
        self._m_log_msg("   点击「仅观察」按钮停止")
        threading.Thread(target=self._m_observe_run, daemon=True).start()

    def _m_observe_run(self):
        """仅观察模式的运行线程"""
        from PID_DEMO.bridge import SerialBridge

        # 获取串口配置
        port=self._tb_port.get().strip() or "AUTO"
        try: baud=int(self._tb_baud.get())
        except: baud=115200

        # 先断开顶部工具栏的连接（如果已连接）
        was_connected = self._conn
        if was_connected and self._bridge:
            self._bridge.disconnect()
            self._conn = False
            self._m_log_msg("[观察] 已断开之前的连接")

        # 创建新的 bridge 实例
        bridge=SerialBridge(port=port,baud=baud)
        if not bridge.connect():
            self._m_log_msg("[错误] 无法打开串口!")
            # 尝试恢复之前的连接
            if was_connected:
                self._conn_toggle()
            self.running=False
            return

        self._m_log_msg(f"[观察] 已连接 {port} @ {baud}")
        self._m_log_msg("[观察] 开始接收数据...")
        bridge.flush()

        count = 0
        while not self._stop_event.is_set():
            try:
                # 从串口读取数据
                sample = bridge.read_sample()
                if sample:
                    speed_L = sample.get("speed_L", 0)
                    speed_R = sample.get("speed_R", 0)
                    target_L = sample.get("target_L", 0)
                    pwm_L = sample.get("pwm_L", 0)

                    # 通过队列更新曲线
                    self.q.put(("m_curve", speed_L))
                    count += 1

                    # 每 50 个点记录一次
                    if count % 50 == 0:
                        self._m_log_msg(f"  #{count}: speed={speed_L} target={target_L} pwm={pwm_L}")
                else:
                    time.sleep(0.01)
            except Exception as e:
                self._m_log_msg(f"错误: {e}")
                time.sleep(0.1)

        # 断开连接并恢复之前的连接
        bridge.disconnect()
        if was_connected:
            self._conn_toggle()
            self._m_log_msg("[观察] 已恢复之前的连接")

        self._m_log_msg(f"[观察] 结束，共接收 {count} 个数据点")
        self.running = False

    def _m_clear(self):self._curve.clear();self._score_var.set("--- %");self._rec_var.set("---");self._m_log.delete(1.0,tk.END)

    def _m_send(self):
        """发送 PID 参数到设备"""
        mode = self._manual_mode.get()

        if mode == "hw":
            # 硬件模式：需要连接设备
            if not self._conn:
                self._m_log_msg("未连接设备，请先连接串口")
                return
            try:
                p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
            except:
                self._m_log_msg("PID 数值无效");return
            self._bridge.set_pid(p,i,d)
            try:
                t=int(self._mtgt.get());self._bridge.set_target(t,t)
            except:
                pass
            self._m_log_msg(f"[硬件] 已发送: P={p:.3f} I={i:.3f} D={d:.3f}")
        else:
            # 仿真模式：只更新参数
            try:
                p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
            except:
                self._m_log_msg("PID 数值无效");return
            self._m_log_msg(f"[仿真] PID 已设置: P={p:.3f} I={i:.3f} D={d:.3f}")

        self.pid={"p":p,"i":i,"d":d}

    def _m_start(self):
        if self.running:self._stop_event.set();return  # 停止
        self._stop_event.clear();self.running=True
        try:p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
        except:p=3.0;i=1.0;d=0.0
        try:tests=int(self._mtests.get());sec=int(self._msec.get());tgt=int(self._mtgt.get())
        except:tests=3;sec=5;tgt=60
        self._curve.clear();self._m_log.delete(1.0,tk.END)

        mode = self._manual_mode.get()
        self._m_log_msg(f"开始测试: P={p:.3f} I={i:.3f} D={d:.3f} [模式: {'硬件' if mode=='hw' else '仿真'}]")

        if mode == "hw":
            # 硬件模式
            if not self._conn:
                self._m_log_msg("未连接设备，请先连接串口")
                self.running = False
                return
            threading.Thread(target=self._m_run_hw,args=(p,i,d,tests,sec,tgt),daemon=True).start()
        else:
            # 仿真模式
            threading.Thread(target=self._m_run_sim,args=(p,i,d,tests,sec,tgt),daemon=True).start()

    def _m_run_hw(self,p,i,d,tests,sec,tgt):
        """硬件模式测试"""
        from PID_DEMO.bridge import SerialBridge

        self._m_log_msg("[硬件] 开始测试...")

        # 获取串口配置
        port=self._tb_port.get().strip() or "AUTO"
        try: baud=int(self._tb_baud.get())
        except: baud=115200

        self._m_log_msg(f"[硬件] 串口: {port} @ {baud}")

        # 先断开顶部工具栏的连接（如果已连接）
        was_connected = self._conn
        if was_connected and self._bridge:
            self._m_log_msg("[硬件] 断开之前的连接...")
            try:
                self._bridge.disconnect()
            except:
                pass
            self._conn = False
            time.sleep(0.5)  # 等待串口释放

        # 创建新的 bridge 实例
        self._m_log_msg("[硬件] 创建新连接...")
        bridge=SerialBridge(port=port,baud=baud)

        try:
            if not bridge.connect():
                self._m_log_msg("[错误] 无法打开串口!")
                self.running=False
                return
        except Exception as e:
            self._m_log_msg(f"[错误] 连接失败: {e}")
            self.running=False
            return

        self._m_log_msg(f"[硬件] 已连接，发送 PID: P={p:.3f} I={i:.3f} D={d:.3f}")

        # 发送 PID 参数
        try:
            bridge.set_pid(p,i,d)
            time.sleep(0.2)
            bridge.flush()  # 清空 MCU 响应
        except Exception as e:
            self._m_log_msg(f"[错误] 发送 PID 失败: {e}")
            bridge.disconnect()
            self.running=False
            return

        # 设置目标（使用 checked 版本，等待 MCU 确认）
        self._m_log_msg(f"[硬件] 设置目标: {tgt}")
        try:
            if not bridge.set_target_checked(tgt,tgt,timeout_s=3.0):
                self._m_log_msg("[警告] 未收到目标确认，继续...")
            bridge.flush()  # 清空 MCU 响应
        except Exception as e:
            self._m_log_msg(f"[错误] 设置目标失败: {e}")
            bridge.disconnect()
            self.running=False
            return

        # 等待 MCU 开始发送数据
        self._m_log_msg("[硬件] 等待数据...")
        samples = bridge.read_samples(5,timeout_s=6.0)

        if len(samples) < 2:
            self._m_log_msg(f"[错误] 只收到 {len(samples)} 个数据点!")
            self._m_log_msg("[提示] 请检查 MCU 是否在发送 CSV 数据")
            bridge.disconnect()
            self.running = False
            return

        # 检查是否有速度数据
        has_speed = any(s.get("speed_L", 0) > 0 for s in samples)
        if not has_speed:
            self._m_log_msg("[警告] 速度为 0!")
            self._m_log_msg("[提示] 请按 PA25 启动 MCU，然后重新测试")
            bridge.disconnect()
            self.running = False
            return

        self._m_log_msg(f"[硬件] 收到 {len(samples)} 点数据，开始测试")

        all_m=[]
        for ti in range(tests):
            if self._stop_event.is_set():self._m_log_msg("[已停止]");break
            self._m_log_msg(f"  第{ti+1}次测试 ({sec}秒)...")

            from PID_DEMO.buffer import SpeedBuffer
            buf=SpeedBuffer(200)
            start_time=time.time()
            count=0

            # 使用 read_samples 批量读取
            target_samples = int(sec * 50)  # 假设 50Hz 采样率
            samples = []
            while len(samples) < target_samples and time.time()-start_time < sec+2:
                if self._stop_event.is_set():break
                batch = bridge.read_samples(min(10, target_samples-len(samples)), timeout_s=0.5)
                samples.extend(batch)
                if batch:
                    for s in batch:
                        speed=s.get("speed_L",0)
                        self.q.put(("m_curve",speed))
                    count += len(batch)

            if count>0:
                # 计算指标
                from PID_DEMO.buffer import SpeedBuffer as SB
                calc_buf = SB(200)
                for s in samples:
                    calc_buf.add(s)
                m = calc_buf.calculate_metrics()
                all_m.append(m)
                self._m_log_msg(f"  第{ti+1}次: {count}点 速度={m.get('avg_speed',0):.1f} 误差={m['avg_error']:.1f}")
            else:
                self._m_log_msg(f"  第{ti+1}次: 无数据!")

        # 断开连接
        bridge.disconnect()

        if all_m:
            avg_err=sum(x["avg_error"] for x in all_m)/len(all_m)
            avg_over=sum(x.get("overshoot",0) for x in all_m)/len(all_m)
            score=max(0,100-avg_err*3-avg_over*0.5)
            self.q.put(("score",f"{score:.1f} %"))
            rec_p=p*(0.7+0.3*score/100);rec_i=i*(0.5+0.5*score/100) if score<70 else i
            self.q.put(("rec",f"P={rec_p:.3f}  I={rec_i:.3f}"))
            self._m_log_msg(f"[硬件] 稳定性: {score:.1f}% | 推荐: P={rec_p:.3f} I={rec_i:.3f}")
        else:
            self._m_log_msg("[硬件] 未获取到任何有效数据!")

        # 断开连接并恢复之前的连接
        bridge.disconnect()
        if was_connected:
            self._conn_toggle()
            self._m_log_msg("[硬件] 已恢复之前的连接")

        self.running=False

    def _m_run_sim(self,p,i,d,tests,sec,tgt):
        """仿真模式测试 — 同一个 sim 连续运行, 不重置"""
        from PID_DEMO.car_model import CarSimulator
        from PID_DEMO.buffer import SpeedBuffer
        all_m=[]
        motor_params = self.config.get("SIM_MOTOR_PARAMS", None)
        sim=CarSimulator(motor_params=motor_params);sim.target=tgt;sim.set_pid(p,i,d)
        self.q.put(("target",tgt))
        for ti in range(tests):
            if self._stop_event.is_set():self._m_log_msg("[已停止]");break
            buf=SpeedBuffer(200)
            for _ in range(int(sec*50)):
                s=sim.step();buf.add(s)
                self.q.put(("m_curve",s.get("speed_L",0)))
                time.sleep(0.008)
            m=buf.calculate_metrics();all_m.append(m)
            self._m_log_msg(f"  第{ti+1}次: 误差={m['avg_error']:.1f} 超调={m['overshoot']:.1f}% [{m.get("status_cn", m["status"])}]")
        avg_err=sum(x["avg_error"] for x in all_m)/len(all_m)
        avg_over=sum(x["overshoot"] for x in all_m)/len(all_m)
        score=max(0,100-avg_err*3-avg_over*0.5)
        self.q.put(("score",f"{score:.1f} %"))
        rec_p=p*(0.7+0.3*score/100);rec_i=i*(0.5+0.5*score/100) if score<70 else i
        self.q.put(("rec",f"P={rec_p:.3f}  I={rec_i:.3f}"))
        self._m_log_msg(f"[仿真] 稳定性: {score:.1f}% | 推荐: P={rec_p:.3f} I={rec_i:.3f}")
        self.running=False

    def _m_model(self):
        try:p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
        except:p=3.0;i=1.0;d=0.0
        try:tgt=int(self._mtgt.get())
        except:tgt=60
        from PID_DEMO.car_model import CarSimulator
        from PID_DEMO.buffer import SpeedBuffer
        from PID_DEMO.llm.client import LLMTuner
        motor_params = self.config.get("SIM_MOTOR_PARAMS", None)
        sim=CarSimulator(motor_params=motor_params);sim.target=tgt;sim.set_pid(p,i,d)
        buf=SpeedBuffer(200)
        for _ in range(250):
            s=sim.step();buf.add(s)
            self.q.put(("m_curve",s.get("speed_L",0)))
        m=buf.calculate_metrics()
        tuner=LLMTuner(self.config)
        self._m_log_msg("请求 LLM 评估...")
        res=tuner.analyze(buf.to_prompt_data(),"")
        if res.get("p",-1)>0:
            rec=f"P={res['p']:.3f}  I={res['i']:.3f}"
            msg=f"LLM 分析: {res.get('analysis_summary','')}\n\n推荐 PID: {rec}"
        else:
            rec=f"P={p*0.9:.3f}  I={i*1.1:.3f}"
            msg=f"LLM 不可用 (检查 API Key)\n\n规则推荐: {rec}"
        self._m_log_msg(f"评估完成: 误差={m['avg_error']:.1f} [{m.get("status_cn", m["status"])}]")
        self._rec_var.set(rec);self.q.put(("rec",rec))
        score=max(0,100-m["avg_error"]*3-m["overshoot"]*0.5)
        self.q.put(("score",f"{score:.1f} %"))
        messagebox.showinfo("模型评估结果",msg+f"\n\n当前: P={p:.3f} I={i:.3f} D={d:.3f}\n误差={m['avg_error']:.1f} 超调={m['overshoot']:.1f}%")

    def _m_log_msg(self,msg):self.q.put(("m_log",msg))

    # ═══ 仿真设置页面 ═══
    def _build_sim_cfg(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["sim_cfg"]=pg
        c=_card(pg);c.pack(fill=tk.BOTH,expand=True)
        _section_label(c,"仿真电机参数","匹配真实 MG310 + TB6612 物理特性")

        sim_params = self.config.get("SIM_MOTOR_PARAMS", {})
        from PID_DEMO.car_model import DEFAULT_MOTOR_PARAMS
        defaults = dict(DEFAULT_MOTOR_PARAMS)
        defaults.update(sim_params)

        self._sim_vars = {}
        rows = [
            ("base_speed",   "基础速度",  "无控制量时电机转速 (脉冲/20ms)", "50"),
            ("max_speed",    "最大速度",  "满 PWM 时电机转速",             "120"),
            ("deadzone",     "PWM 死区",  "低于此值电机不转",             "800"),
            ("inertia",      "惯性系数",  "响应延迟 (步数, 越大越慢)",    "4"),
            ("noise",        "噪声幅度",  "速度噪声标准差",               "0.5"),
            ("control_limit","控制上限",  "PID 输出限幅",                 "1200"),
        ]
        for key, label, tip, fallback in rows:
            rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
            _lbl(rw,label,F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
            v=tk.StringVar(value=str(defaults.get(key, fallback)))
            tk.Entry(rw,textvariable=v,font=F["m"],fg=C["text"],bg=C["bg"],
                     relief=tk.FLAT,width=8,insertbackground=C["accent"],
                     highlightbackground=C["border"],highlightthickness=1).pack(side=tk.LEFT,ipady=3,padx=(0,8))
            _lbl(rw,tip,F["s"],C["muted"]).pack(side=tk.LEFT)
            self._sim_vars[key]=v

        btn_row=tk.Frame(c,bg=C["card"]);btn_row.pack(pady=(16,0))
        _btn(btn_row,"保存仿真参数",self._save_sim_cfg,pri=True).pack(side=tk.LEFT,padx=(0,8))
        _btn(btn_row,"恢复默认",self._reset_sim_cfg).pack(side=tk.LEFT)

    def _save_sim_cfg(self):
        params = {}
        for key, v in self._sim_vars.items():
            try: params[key] = float(v.get())
            except: pass
        self.config["SIM_MOTOR_PARAMS"] = params
        # 写入 config.json
        try:
            import json
            cfg = dict(self.config)
            with open(self._cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("", "仿真参数已保存")
        except Exception as e:
            messagebox.showerror("", str(e))

    def _reset_sim_cfg(self):
        from PID_DEMO.car_model import DEFAULT_MOTOR_PARAMS
        for key, val in DEFAULT_MOTOR_PARAMS.items():
            if key in self._sim_vars:
                self._sim_vars[key].set(str(val))

    # ═══ LLM 设置页面 ═══
    def _build_settings(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["settings"]=pg
        c=_card(pg);c.pack(fill=tk.BOTH,expand=True)
        _section_label(c,"LLM 配置","可选，用于自动推荐参数")

        # 快捷模板
        r0=tk.Frame(c,bg=C["card"]);r0.pack(fill=tk.X,pady=(0,8))
        _lbl(r0,"快捷模板:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,6))

        self.PRESETS={
            "DeepSeek":  {"url":"https://api.deepseek.com","model":"deepseek-v4-pro","provider":"openai",
                          "models":["deepseek-v4-pro","deepseek-v4-flash","deepseek-chat","deepseek-reasoner"]},
            "ChatGPT":   {"url":"https://api.openai.com/v1","model":"gpt-5.1","provider":"openai",
                          "models":["gpt-5.1","gpt-5","gpt-4.1","o4-mini"]},
            "MiniMax":   {"url":"https://api.minimax.chat/v1","model":"MiniMax-M2.5","provider":"openai",
                          "models":["MiniMax-M2.5","MiniMax-Text-01","abab7-chat"]},
            "Claude":    {"url":"https://api.anthropic.com","model":"claude-opus-4-8","provider":"anthropic",
                          "models":["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"]},
            "豆包":      {"url":"https://ark.cn-beijing.volces.com/api/v3","model":"doubao-pro-256k","provider":"openai",
                          "models":["doubao-pro-256k","doubao-pro-128k","doubao-lite-32k"]},
        }
        self._preset_var=tk.StringVar()
        cb=ttk.Combobox(r0,textvariable=self._preset_var,values=list(self.PRESETS.keys()),state="readonly",width=10,font=F["b"])
        cb.pack(side=tk.LEFT,padx=(0,6))
        cb.bind("<<ComboboxSelected>>",lambda e:self._apply_preset())
        _btn(r0,"应用",lambda:self._apply_preset()).pack(side=tk.LEFT)

        self._sv={}
        # API Key (text)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"API Key",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        v=tk.StringVar(value=str(self.config.get("LLM_API_KEY","")))
        tk.Entry(rw,textvariable=v,show="*",font=F["m"],fg=C["text"],bg=C["bg"],
                 relief=tk.FLAT,width=42,insertbackground=C["accent"],
                 highlightbackground=C["border"],highlightthickness=1).pack(side=tk.LEFT,ipady=4)
        self._sv["LLM_API_KEY"]=v

        # Base URL (text)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"Base URL",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        v=tk.StringVar(value=str(self.config.get("LLM_API_BASE_URL","")))
        tk.Entry(rw,textvariable=v,font=F["m"],fg=C["text"],bg=C["bg"],
                 relief=tk.FLAT,width=42,insertbackground=C["accent"],
                 highlightbackground=C["border"],highlightthickness=1).pack(side=tk.LEFT,ipady=4)
        self._sv["LLM_API_BASE_URL"]=v

        # Provider (dropdown)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"服务商",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        self._prov_var=tk.StringVar(value=str(self.config.get("LLM_PROVIDER","openai")))
        pc=ttk.Combobox(rw,textvariable=self._prov_var,values=["openai","anthropic"],state="readonly",width=14,font=F["m"])
        pc.pack(side=tk.LEFT)
        self._sv["LLM_PROVIDER"]=self._prov_var

        # Model (dropdown)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"模型名称",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        self._model_var=tk.StringVar(value=str(self.config.get("LLM_MODEL_NAME","gpt-4o")))
        all_models=sorted(set(m for p in self.PRESETS.values() for m in p["models"]))
        mc=ttk.Combobox(rw,textvariable=self._model_var,values=all_models,width=24,font=F["m"])
        mc.pack(side=tk.LEFT)
        mc.bind("<FocusIn>",lambda e:mc.config(values=sorted(set(m for p in self.PRESETS.values() for m in p["models"]))))
        self._sv["LLM_MODEL_NAME"]=self._model_var

        # 状态行
        self._llm_status_var=tk.StringVar(value="")
        tk.Label(c,textvariable=self._llm_status_var,font=F["s"],fg=C["sub"],bg=C["card"],wraplength=500,justify=tk.LEFT).pack(fill=tk.X,pady=(8,0))

        # 按钮行
        btn_row=tk.Frame(c,bg=C["card"]);btn_row.pack(pady=(8,0))
        _btn(btn_row,"保存配置",self._save_cfg,pri=True).pack(side=tk.LEFT,padx=(0,8))
        _btn(btn_row,"测试连接",self._test_llm).pack(side=tk.LEFT)

    def _apply_preset(self,presets=None):
        name=self._preset_var.get()
        if name not in self.PRESETS:return
        p=self.PRESETS[name]
        self._sv["LLM_API_BASE_URL"].set(p["url"])
        self._model_var.set(p["model"])
        self._prov_var.set(p["provider"])
        # update model dropdown with this provider's models
        for w in self._pages["settings"].winfo_children():
            if isinstance(w,tk.Frame):
                for c in w.winfo_children():
                    if isinstance(c,tk.Frame):
                        for r in c.winfo_children():
                            if isinstance(r,tk.Frame):
                                for x in r.winfo_children():
                                    if isinstance(x,ttk.Combobox):
                                        cur=x.cget("values")
                                        if cur and any("gpt" in str(v) or "deepseek" in str(v) or "claude" in str(v) or "MiniMax" in str(v) or "doubao" in str(v) for v in cur):
                                            x.config(values=p.get("models",list(cur)))

    def _save_cfg(self):
        cfg={k:v.get() for k,v in self._sv.items()}
        for k in DEFAULT_CONFIG:
            if k not in cfg:cfg[k]=DEFAULT_CONFIG[k]
        try:
            with open(self._cfg_path,"w",encoding="utf-8") as f:json.dump(cfg,f,indent=2,ensure_ascii=False)
            self.config=cfg;messagebox.showinfo("","配置已保存")
        except Exception as e:messagebox.showerror("",str(e))

    def _test_llm(self):
        """测试 LLM 连接"""
        self._llm_status_var.set("测试中...")
        self.root.update()
        def do_test():
            try:
                # 从 GUI 控件读取当前值
                cfg=dict(self.config)
                cfg["LLM_API_KEY"]=self._sv["LLM_API_KEY"].get()
                cfg["LLM_API_BASE_URL"]=self._sv["LLM_API_BASE_URL"].get()
                cfg["LLM_MODEL_NAME"]=self._model_var.get()
                cfg["LLM_PROVIDER"]=self._prov_var.get()
                key=cfg["LLM_API_KEY"]; url=cfg["LLM_API_BASE_URL"]; model=cfg["LLM_MODEL_NAME"]
                if not key or key=="sk-your-key-here":
                    self.q.put(("llm_status","❌ API Key 未填写"));return
                self.q.put(("llm_status",f"连接 {url} ..."))
                from PID_DEMO.llm.client import LLMTuner
                tuner=LLMTuner(cfg)
                res=tuner.analyze("speed=50 target=60 error=10 overshoot=0%")
                if res and res.get("p",0)>0:
                    self.q.put(("llm_status",f"✅ 成功! 模型={model} 返回 P={res['p']:.2f} I={res['i']:.2f}"))
                else:
                    self.q.put(("llm_status",f"❌ 返回无效: {tuner.last_error}"))
            except Exception as e:
                self.q.put(("llm_status",f"❌ 错误: {e}"))
        threading.Thread(target=do_test,daemon=True).start()

    # ═══ 消息轮询 ═══
    def _poll(self):
        auto_logs=[]
        manual_logs=[]
        last_curve=None
        curve_target=None
        last_m_curve=None
        max_msgs=300
        for _ in range(max_msgs):
            try:msg=self.q.get_nowait()
            except queue.Empty:break
            tp,data=msg
            if tp=="pid":
                for k in ("p","i","d"):
                    if k in data and k in self._av:self._av[k].set(f"{data[k]:.3f}")
            elif tp in ("curve","m_curve"):
                if tp=="curve":last_curve=data
                else:last_m_curve=data
            elif tp=="target":curve_target=data
            elif tp=="auto_log":
                auto_logs.append(str(data))
            elif tp=="m_log":
                manual_logs.append(str(data))
            elif tp=="score":self._score_var.set(str(data))
            elif tp=="rec":self._rec_var.set(str(data))
            elif tp=="llm_status":self._llm_status_var.set(str(data))
            elif tp=="done":
                self.running=False;self._stop_event.clear()
                if hasattr(self,'_auto_btn'):
                    self._auto_btn.config(text="开始自动调参",state=tk.NORMAL,bg=C["accent"],fg="white")
        if curve_target is not None:
            self._curve.target=curve_target
        if last_curve is not None or last_m_curve is not None:
            v=last_curve if last_curve is not None else last_m_curve
            self._curve.max_y=max(self._curve.target*2,120)
            self._curve.data.append(v)
            if len(self._curve.data)>self._curve.max_pts:
                del self._curve.data[:-self._curve.max_pts]
            self._curve.draw()
        if auto_logs:
            self._append_log_batch(self._auto_log,auto_logs)
        if manual_logs:
            self._append_log_batch(self._m_log,manual_logs)
        self.root.after(30,self._poll)

    def _append_log_batch(self,widget,lines,max_lines=500):
        widget.insert(tk.END,"\n".join(lines)+"\n")
        line_count=int(widget.index("end-1c").split(".")[0])
        if line_count>max_lines:
            widget.delete("1.0",f"{line_count-max_lines}.0")
        widget.see(tk.END)

def main():
    root=tk.Tk()
    try:root.iconbitmap(default="")
    except:pass
    App(root);root.mainloop()

if __name__=="__main__":main()
