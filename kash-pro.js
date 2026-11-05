
(function(){
'use strict';
if(window.__KASH_PRO__) return;
window.__KASH_PRO__=true;
var API_KEY='kashProApiBase';
var API_DEFAULT=(window.KASH_PRO_CONFIG&&window.KASH_PRO_CONFIG.apiBase)||'http://127.0.0.1:8000';
var apiBase=localStorage.getItem(API_KEY)||API_DEFAULT;
var candles=[],chart=null,candleSeries=null;
var $=function(id){return document.getElementById(id);};
var esc=function(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
var fmt=function(v,d){if(v==null||!Number.isFinite(Number(v)))return '—';return Number(v).toLocaleString(undefined,{maximumFractionDigits:d==null?2:d});};
var pct=function(v){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(2)+'%';};
function api(path,options){options=options||{};return fetch(apiBase.replace(/\/$/,'')+path,Object.assign({},options,{headers:Object.assign({'Content-Type':'application/json'},options.headers||{})})).then(function(r){return r.json().catch(function(){return {};}).then(function(data){if(!r.ok)throw new Error(data.detail||('API error '+r.status));return data;});});}
function error(id,msg){var el=$(id);if(el)el.innerHTML=msg?'<div class="kp-error">'+esc(msg)+'</div>':'';}
function status(msg){var el=$('kpStatus');if(el)el.textContent=msg;}
function activePane(name){document.querySelectorAll('#viewPro [data-kp-pane]').forEach(function(b){b.classList.toggle('active',b.dataset.kpPane===name);});document.querySelectorAll('#viewPro .kp-pane').forEach(function(p){p.classList.toggle('active',p.id==='kp-pane-'+name);});if(name==='chart'&&window.LightweightCharts&&!chart)initChart();}
function metric(label,value){return '<div class="kp-stat"><label>'+esc(label)+'</label><strong>'+esc(value)+'</strong></div>';}
function initChart(){
 if(!window.LightweightCharts||!$('kpChart'))return false;
 if(chart){try{chart.remove();}catch(e){}chart=null;}
 $('kpChart').innerHTML='';
 chart=LightweightCharts.createChart($('kpChart'),{width:$('kpChart').clientWidth,height:$('kpChart').clientHeight,layout:{background:{type:'solid',color:'#081219'},textColor:'#8ba69c',attributionLogo:true},grid:{vertLines:{color:'rgba(130,170,150,.08)'},horzLines:{color:'rgba(130,170,150,.08)'}},rightPriceScale:{borderColor:'rgba(0,230,150,.18)'},timeScale:{borderColor:'rgba(0,230,150,.18)',timeVisible:true,secondsVisible:false},crosshair:{vertLine:{color:'#00a879'},horzLine:{color:'#00a879'}}});
 candleSeries=chart.addSeries(LightweightCharts.CandlestickSeries,{upColor:'#00c98b',downColor:'#ff6177',borderUpColor:'#00c98b',borderDownColor:'#ff6177',wickUpColor:'#00c98b',wickDownColor:'#ff6177'});
 if(window.ResizeObserver){var ro=new ResizeObserver(function(){if(chart&&$('kpChart'))chart.applyOptions({width:$('kpChart').clientWidth,height:$('kpChart').clientHeight});});ro.observe($('kpChart'));}
 if(candles.length)setChartData();
 return true;
}
function setChartData(){
 if(!candleSeries||!candles.length)return;
 candleSeries.setData(candles.map(function(c){return {time:Math.floor(c.time/1000),open:c.open,high:c.high,low:c.low,close:c.close};}));
 chart.timeScale().fitContent();
 var last=candles[candles.length-1],prev=candles[candles.length-2],change=prev?(last.close/prev.close-1)*100:null;
 $('kpLast').textContent=fmt(last.close,6);
 $('kpBarChange').textContent=change==null?'—':(change>=0?'+':'')+pct(change);
 $('kpBarChange').className=change==null?'':' '+(change>=0?'kp-positive':'kp-negative');
 $('kpChartMeta').textContent=candles.length+' candles · timestamps UTC';
}
function loadChart(symbol){
 error('kpChartError','');
 if(!window.LightweightCharts){error('kpChartError','The TradingView chart library did not load. Check that the CDN is allowed by your network/CSP.');return Promise.resolve();}
 symbol=(symbol||$('kpSymbol').value||'BTC/USDT').trim().toUpperCase();
 $('kpSymbol').value=symbol;
 var exchange=$('kpExchange').value,tf=$('kpTimeframe').value;
 return api('/api/market/ohlcv?exchange='+encodeURIComponent(exchange)+'&symbol='+encodeURIComponent(symbol)+'&timeframe='+encodeURIComponent(tf)+'&limit=500').then(function(data){
  candles=data.candles||[];
  if(!chart)initChart();
  setChartData();
  status('API ONLINE · '+exchange.toUpperCase());
  return loadBook(exchange,symbol);
 }).catch(function(e){error('kpChartError',e.message);status('API ERROR');});
}
function loadBook(exchange,symbol){
 return api('/api/market/orderbook?exchange='+encodeURIComponent(exchange)+'&symbol='+encodeURIComponent(symbol)+'&limit=20').then(function(d){
  $('kpSpread').textContent=d.spread_bps==null?'—':fmt(d.spread_bps,2)+' bps';
  $('kpBids').innerHTML=(d.bids||[]).slice(0,10).map(function(x){return '<div class="kp-listrow"><span>'+fmt(x[0],6)+'</span><strong>'+fmt(x[1],4)+'</strong></div>';}).join('')||'No bids returned.';
  $('kpAsks').innerHTML=(d.asks||[]).slice(0,10).map(function(x){return '<div class="kp-listrow"><span>'+fmt(x[0],6)+'</span><strong>'+fmt(x[1],4)+'</strong></div>';}).join('')||'No asks returned.';
 }).catch(function(e){$('kpSpread').textContent='Unavailable';$('kpBids').textContent=e.message;$('kpAsks').textContent=e.message;});
}
function scan(){
 error('kpScanError','');
 $('kpScan').disabled=true;$('kpScan').textContent='SCANNING…';
 var exchange=$('kpExchange').value,quote=$('kpQuote').value,limit=$('kpLimit').value;
 return api('/api/market/summary?exchange='+encodeURIComponent(exchange)+'&quote='+encodeURIComponent(quote)+'&limit='+limit).then(function(d){
  $('kpMarkets').innerHTML=(d.markets||[]).map(function(m){var up=m.change_pct!=null&&m.change_pct>=0;return '<tr><td><strong>'+esc(m.symbol)+'</strong></td><td>'+fmt(m.last,6)+'</td><td class="'+(up?'kp-positive':'kp-negative')+'">'+(m.change_pct==null?'—':(up?'+':'')+pct(m.change_pct))+'</td><td>'+fmt(m.quote_volume,0)+'</td><td>'+fmt(m.bid,6)+'</td><td>'+fmt(m.ask,6)+'</td><td><button class="kp-button ghost" data-kp-open="'+esc(m.symbol)+'">OPEN</button></td></tr>';}).join('')||'<tr><td colspan="7">No markets were returned for this quote asset.</td></tr>';
  $('kpMarkets').querySelectorAll('[data-kp-open]').forEach(function(b){b.addEventListener('click',function(){ $('kpSymbol').value=b.getAttribute('data-kp-open');activePane('chart');loadChart(b.getAttribute('data-kp-open'));});});
  $('kpScanMeta').textContent=d.count+' markets · '+exchange.toUpperCase()+' · '+new Date(d.updated_at).toLocaleTimeString();
  status('API ONLINE · '+exchange.toUpperCase());
 }).catch(function(e){error('kpScanError',e.message);status('API ERROR');}).finally(function(){$('kpScan').disabled=false;$('kpScan').textContent='SCAN MARKETS';});
}
function runBacktest(){
 error('kpBacktestError','');
 if(candles.length<60){error('kpBacktestError','Load at least 60 candles in PRO CHART before running a backtest.');return;}
 var strategy=$('kpStrategy').value;
 var body={candles:candles,strategy:strategy,timeframe:$('kpTimeframe').value,fast_period:Number($('kpFast').value),slow_period:Number($('kpSlow').value),rsi_period:Number($('kpFast').value),rsi_entry:Number($('kpRsiEntry').value),rsi_exit:Number($('kpRsiExit').value),initial_cash:Number($('kpCapital').value),exposure_fraction:Number($('kpExposure').value),fee_bps:Number($('kpFee').value),slippage_bps:Number($('kpSlip').value)};
 $('kpRunBacktest').disabled=true;$('kpRunBacktest').textContent='RUNNING…';
 api('/api/backtest',{method:'POST',body:JSON.stringify(body)}).then(function(d){
  var m=d.metrics||{};
  $('kpBacktestResults').innerHTML=metric('TOTAL RETURN',pct(m.total_return_pct))+metric('MAX DRAWDOWN',pct(m.max_drawdown_pct))+metric('SHARPE',fmt(m.sharpe,2))+metric('SORTINO',fmt(m.sortino,2))+metric('WIN RATE',pct(m.win_rate_pct))+metric('PROFIT FACTOR',m.profit_factor==='infinite'?'∞':fmt(m.profit_factor,2))+metric('TRADE COUNT',fmt(m.trade_count,0))+metric('ENDING EQUITY',fmt(m.ending_equity,2))+metric('CAGR',pct(m.cagr_pct))+'<div class="kp-wide kp-muted">Execution: '+esc(d.assumptions.execution)+'. Fee '+esc(d.assumptions.fee_bps_each_side)+' bps/side; slippage '+esc(d.assumptions.slippage_bps_each_side)+' bps/side. The final open position is closed at the last candle close.</div><div class="kp-wide kp-table-wrap"><table><thead><tr><th>ENTRY TIME</th><th>EXIT TIME</th><th>ENTRY</th><th>EXIT</th><th>NET P&L</th><th>RETURN</th></tr></thead><tbody>'+(d.trades||[]).slice(-20).reverse().map(function(t){return '<tr><td>'+new Date(t.entry_time).toLocaleString()+'</td><td>'+new Date(t.exit_time).toLocaleString()+'</td><td>'+fmt(t.entry_price,6)+'</td><td>'+fmt(t.exit_price,6)+'</td><td class="'+(t.net_pnl>=0?'kp-positive':'kp-negative')+'">'+fmt(t.net_pnl,2)+'</td><td>'+pct(t.return_pct)+'</td></tr>';}).join('')+'</tbody></table></div>';
  if(d.warnings&&d.warnings.length)$('kpBacktestResults').innerHTML+='<div class="kp-wide kp-muted">'+d.warnings.map(esc).join('<br>')+'</div>';
 }).catch(function(e){error('kpBacktestError',e.message);}).finally(function(){$('kpRunBacktest').disabled=false;$('kpRunBacktest').textContent='RUN BACKTEST';});
}
function parseReturns(){return $('kpReturns').value.split(/[\s,;]+/).filter(Boolean).map(Number);}
function runRisk(){
 error('kpRiskError','');$('kpRunRisk').disabled=true;
 api('/api/analytics',{method:'POST',body:JSON.stringify({returns:parseReturns(),periods_per_year:Number($('kpPeriods').value),initial_equity:Number($('kpRiskCapital').value)})}).then(function(d){
  $('kpRiskResults').innerHTML=metric('TOTAL RETURN',pct(d.total_return_pct))+metric('CAGR',pct(d.cagr_pct))+metric('VOLATILITY',pct(d.annualized_volatility_pct))+metric('SHARPE',fmt(d.sharpe,2))+metric('SORTINO',fmt(d.sortino,2))+metric('MAX DRAWDOWN',pct(d.max_drawdown_pct))+metric('CALMAR',fmt(d.calmar,2))+metric('POSITIVE PERIODS',pct(d.positive_period_pct))+metric('ENDING EQUITY',fmt(d.ending_equity,2))+'<div class="kp-wide kp-muted">'+d.count+' periods analysed. '+(d.quantstats_available?'QuantStats '+esc(d.quantstats_version)+' is installed.':'Native analytics calculation used.')+'</div>';
 }).catch(function(e){error('kpRiskError',e.message);}).finally(function(){$('kpRunRisk').disabled=false;});
}
function runMonte(){
 error('kpRiskError','');$('kpRunMonte').disabled=true;
 api('/api/monte-carlo',{method:'POST',body:JSON.stringify({returns:parseReturns(),initial_equity:Number($('kpRiskCapital').value),paths:1000,steps:100,seed:42})}).then(function(d){
  var p=d.ending_equity_percentiles||{};
  $('kpRiskResults').innerHTML=metric('5TH PERCENTILE',fmt(p['5'],2))+metric('MEDIAN OUTCOME',fmt(p['50'],2))+metric('95TH PERCENTILE',fmt(p['95'],2))+metric('PROBABILITY OF LOSS',pct(d.probability_of_loss_pct))+metric('PATHS',fmt(d.paths,0))+metric('HORIZON',fmt(d.steps,0)+' periods')+'<div class="kp-wide kp-muted">Bootstrap scenario from historical returns. Not a forecast or guarantee.</div>';
 }).catch(function(e){error('kpRiskError',e.message);}).finally(function(){$('kpRunMonte').disabled=false;});
}
function health(){api('/health').then(function(d){status(d.ok?'API ONLINE · READ ONLY':'API ERROR');}).catch(function(){status('API NOT CONNECTED');});}
function bind(){
 document.querySelectorAll('#viewPro [data-kp-pane]').forEach(function(b){b.addEventListener('click',function(){activePane(b.dataset.kpPane);});});
 $('kpScan').addEventListener('click',scan);
 $('kpLoadChart').addEventListener('click',function(){loadChart();});
 $('kpRunBacktest').addEventListener('click',runBacktest);
 $('kpRunRisk').addEventListener('click',runRisk);
 $('kpRunMonte').addEventListener('click',runMonte);
 $('kpExchange').addEventListener('change',function(){status('EXCHANGE CHANGED · REFRESH DATA');});
 if(window.ResizeObserver&&$('kpChart')){var observer=new ResizeObserver(function(){if(chart&&$('kpChart').clientWidth)chart.applyOptions({width:$('kpChart').clientWidth,height:$('kpChart').clientHeight});});observer.observe($('kpChart'));}
 var script=document.createElement('script');
 script.src='https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js';
 script.async=true;script.onload=function(){if(candles.length&&chart)setChartData();};script.onerror=function(){error('kpChartError','Could not load Lightweight Charts 5.2.1 from unpkg.');};
 document.head.appendChild(script);
 health();
}
window.KashPro={onOpen:function(){health();},scan:scan,loadChart:loadChart,setApiBase:function(url){apiBase=String(url||'').replace(/\/$/,'');localStorage.setItem(API_KEY,apiBase);health();}};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
})();
