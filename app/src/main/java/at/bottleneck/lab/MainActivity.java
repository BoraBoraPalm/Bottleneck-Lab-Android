package at.bottleneck.lab;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.View;
import android.widget.*;
import org.json.*;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;

public class MainActivity extends Activity {
  final ExecutorService worker=Executors.newSingleThreadExecutor();
  LinearLayout list; TextView info; Button refresh; Spinner coverage;
  final String[] stocks=("NEX.PA,VRT,MU,FCX,CEG,XYL,ROK,RTX,PRY.MI,ETN,AMAT,SCCO,NRG,WTRG,EMR,LMT,GEV,NVT,LRCX,BHP,VST,AWK,HON,NOC,DELL,KLAC,RIO,NEE,ECL,PH,GD,HUBB,SMCI,ASML,TECK,DUK,IEX,CAT,HII,ANET,TSM,AA,SO,PNR,DE,LHX,PWR,CSCO,AVGO,MP,EXC,AOS,FANUY,AXON,HPE,MRVL,ALB,EIX,WTS,ZBRA,PANW,ABB,APH,NVDA,LAC,FSLR,BMI,SYM,CRWD,SU.PA,GLW,AMD,CCJ,GXO,FTNT,EQIX,QCOM,UUUU,BWXT,UPS,DLR,ADI,WCC,MPWR,BE,POWL,TER,OKLO,GNRC,ONTO,CRDO,SNDK").split(",");
  static class Quote { String symbol,date;double price,mom,atr,score,buy,stop; }
  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    ScrollView sc=new ScrollView(this);
    LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setPadding(24,32,24,24);
    sc.addView(root);setContentView(sc);
    TextView head=new TextView(this);head.setText("Bottleneck Lab");head.setTextSize(26);head.setTextColor(Color.rgb(9,65,66));root.addView(head);
    TextView sub=new TextView(this);sub.setText("Research-Prototyp · Inoffizielle Kursquelle · Keine Orders");root.addView(sub);
    coverage=new Spinner(this);String[] levels={"12 Titel","24 Titel","48 Titel","92 Titel"};
    ArrayAdapter<String> adapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,levels);
    coverage.setAdapter(adapter);coverage.setSelection(1);root.addView(coverage);
    refresh=new Button(this);refresh.setText("Echte Marktdaten aktualisieren");root.addView(refresh);
    info=new TextView(this);info.setText("Noch keine Daten. Yahoo Finance kann Abfragen blockieren.");root.addView(info);
    list=new LinearLayout(this);list.setOrientation(1);root.addView(list);
    TextView note=new TextView(this);note.setText("\nRanking nur nach Kursmomentum. Ohne Fundamentalhistorie und nachgewiesene Engpässe keine validierte Investmentstrategie. Kauf-/Stop-Kurse sind ATR-Heuristiken; Kurslücken können Stops überspringen.");root.addView(note);
    refresh.setOnClickListener(v->load());
  }
  String fetch(String symbol) throws Exception {
    String last="";
    for(String host:new String[]{"query1.finance.yahoo.com","query2.finance.yahoo.com"}){
      HttpURLConnection c=null;
      try{
        URL url=new URL("https://"+host+"/v8/finance/chart/"+URLEncoder.encode(symbol,"UTF-8")+"?range=6mo&interval=1d");
        c=(HttpURLConnection)url.openConnection();
        c.setConnectTimeout(6000);c.setReadTimeout(7000);
        c.setRequestProperty("User-Agent","Mozilla/5.0");
        if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode());
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        try(InputStream in=c.getInputStream()){byte[] buf=new byte[4096];int n;while((n=in.read(buf))>=0){if(b.size()+n>1700000)throw new IOException("Oversized response");b.write(buf,0,n);}}
        return b.toString("UTF-8");
      }catch(Exception e){last=e.getMessage();}
      finally{if(c!=null)c.disconnect();}
    }
    throw new IOException(symbol+": "+last);
  }
  Quote quote(String ticker)throws Exception{
    JSONObject r=new JSONObject(fetch(ticker)).getJSONObject("chart").getJSONArray("result").getJSONObject(0);
    JSONArray times=r.getJSONArray("timestamp");
    JSONObject q=r.getJSONObject("indicators").getJSONArray("quote").getJSONObject(0);
    JSONArray close=q.getJSONArray("close"),high=q.getJSONArray("high"),low=q.getJSONArray("low");
    ArrayList<Double> prices=new ArrayList<>(),tr=new ArrayList<>();
    String date="";double previous=Double.NaN;
    for(int i=0;i<close.length();i++){
      double p=close.optDouble(i,Double.NaN),h=high.optDouble(i,Double.NaN),l=low.optDouble(i,Double.NaN);
      if(!Double.isFinite(p)||p<=0||!Double.isFinite(h)||!Double.isFinite(l))continue;
      prices.add(p);if(Double.isFinite(previous))tr.add(Math.max(h-l,Math.max(Math.abs(h-previous),Math.abs(l-previous))));
      previous=p;date=Instant.ofEpochSecond(times.getLong(i)).atZone(ZoneOffset.UTC).toLocalDate().toString();
    }
    int n=prices.size();if(n<65||tr.size()<14)throw new IOException("Zu wenige gültige Kurstage");
    double p=prices.get(n-1),mom=p/prices.get(n-61)-1,atr=0;
    for(int i=tr.size()-14;i<tr.size();i++)atr+=tr.get(i)/14;
    double vol=atr/p,disc=Math.max(.01,Math.min(.09,vol)),dist=Math.max(.08,Math.min(.30,vol*2.8));
    Quote x=new Quote();x.symbol=ticker;x.price=p;x.mom=mom;x.atr=vol;x.date=date;
    x.buy=p*(1-disc);x.stop=x.buy*(1-dist);
    x.score=Math.max(0,Math.min(100,50+200*mom));return x;
  }
  void load(){
    refresh.setEnabled(false);list.removeAllViews();info.setText("Lade Kurse …");
    int requested=new int[]{12,24,48,92}[coverage.getSelectedItemPosition()];
    worker.execute(()->{
      List<Quote> found=new ArrayList<>();int errors=0;
      for(int i=0;i<Math.min(requested,stocks.length);i++){
        final int pos=i;runOnUiThread(()->info.setText("Prüfe "+(pos+1)+"/"+requested+" · "+stocks[pos]));
        try{found.add(quote(stocks[i]));}catch(Exception e){errors++;}
      }
      found.sort((a,b)->Double.compare(b.score,a.score));
      final int missing=errors;
      runOnUiThread(()->{
        refresh.setEnabled(true);info.setText(found.size()+" von "+requested+" Aktien geladen; "+missing+" fehlgeschlagen. Datenanbieter: Yahoo Finance (inoffiziell).");
        if(found.isEmpty()){info.setText("Kein Abruf erfolgreich. Yahoo Finance möglicherweise nicht erreichbar.");return;}
        int rank=0;
        for(Quote q:found){
          if(rank++>=10)break;
          TextView t=new TextView(this);t.setTextSize(17);t.setPadding(10,18,10,18);
          t.setText(rank+". "+q.symbol+"   "+String.format(Locale.GERMANY,"%.2f",q.price)+"\n"+q.date+" · Momentum 60 Tage: "+String.format(Locale.GERMANY,"%.1f",q.mom*100)+" %\nBuy (Modell): "+String.format(Locale.GERMANY,"%.2f",q.buy)+"   Stop: "+String.format(Locale.GERMANY,"%.2f",q.stop));
          list.addView(t);View line=new View(this);line.setBackgroundColor(0xffdce5e7);list.addView(line,new LinearLayout.LayoutParams(-1,1));
        }
      });
    });
  }
  @Override public void onDestroy(){worker.shutdownNow();super.onDestroy();}
}