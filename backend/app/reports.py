import csv
import io
import json
from xml.sax.saxutils import escape

def render(snapshot,fmt):
    if fmt=='csv':
        stream=io.StringIO(); writer=csv.writer(stream); writer.writerow(['section','field','value'])
        def safe(value):
            text=str(value)
            return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
        def flatten(value,prefix=''):
            if isinstance(value,dict):
                for k,v in value.items(): yield from flatten(v,f'{prefix}.{k}' if prefix else k)
            elif isinstance(value,list):
                for i,v in enumerate(value): yield from flatten(v,f'{prefix}[{i}]')
            else: yield prefix,value
        for key,value in flatten(snapshot): writer.writerow([safe(key.split('.')[0]),safe(key),safe(value)])
        return stream.getvalue().encode('utf-8-sig'),'text/csv'
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    stream=io.BytesIO(); styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('SmallBody',parent=styles['BodyText'],fontSize=9,leading=13,spaceAfter=6))
    doc=SimpleDocTemplate(stream,pagesize=(595,842),rightMargin=44,leftMargin=44,topMargin=48,bottomMargin=46)
    story=[]
    def text(value,style='SmallBody'):
        # Built-in PDF fonts: substitute unsupported characters instead of missing glyphs.
        safe=str(value).encode('cp1252','replace').decode('cp1252')
        return Paragraph(escape(safe).replace('\n','<br/>'),styles[style])
    def section(title,body): story.append(KeepTogether([Spacer(1,10),text(title,'Heading2'),text(body)]))
    inv=snapshot['investigation']; target=snapshot['target']; risk=snapshot['assessment']['explanation']; report=snapshot.get('agent_report') or {}
    story.extend([text('OWNERSHIPGRAPH AI','Title'),text('Evidence-led investigation report','Heading2'),text(f"Investigation #{inv['id']} | Generated {snapshot['generated_at']}"),text('SYNTHETIC DEMONSTRATION RECORDS' if target['synthetic'] else 'SOURCE RECORDS - verification status must be checked')])
    section('1. Investigation overview',f"{inv['title']} | Status: {inv['status']}\n{report.get('summary','Deterministic risk assessment snapshot.')}")
    section('2. Target entity',f"{target['entity_name']} | {target['entity_type']} | {target['jurisdiction']} | {target.get('registration_number') or 'No registration identifier'} | SRC-{target['source_id']}")
    own=report.get('ownership',{})
    section('3. Ownership structure',f"{len(own.get('paths',[]))} upstream person paths. Aggregation withheld: {own.get('aggregation_withheld','Ownership workflow not run')}. Threshold: {own.get('threshold','Unavailable')}% (illustrative).")
    if own.get('paths'):
        from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon
        paths=own['paths'][:4]
        drawing=Drawing(500,30+len(paths)*35)
        drawing.add(String(0,drawing.height-10,'Ownership path overview (entity IDs; evidence listed below)',fontName='Helvetica',fontSize=8,fillColor=colors.HexColor('#67828a')))
        for row,path in enumerate(paths):
            ids=path['entity_ids'];step=min(100,430/max(1,len(ids)-1));y=drawing.height-37-row*35
            for i,node in enumerate(ids):
                x=5+i*step
                if i:
                    drawing.add(Line(x-step+36,y+9,x-3,y+9,strokeColor=colors.HexColor('#92b4ad')))
                    drawing.add(Polygon([x-3,y+9,x-8,y+12,x-8,y+6],fillColor=colors.HexColor('#92b4ad'),strokeColor=None))
                drawing.add(Rect(x,y,34,18,rx=4,fillColor=colors.HexColor('#e6f2ee'),strokeColor=colors.HexColor('#b6d0c7')))
                drawing.add(String(x+17,y+5,f'#{node}',fontName='Helvetica',fontSize=8,textAnchor='middle',fillColor=colors.HexColor('#2f665a')))
        story.append(drawing)
    section('4. Potential beneficial owners','\n'.join(f"{o['name']}: combined {str(o['combined_percentage'])+'%' if o['combined_percentage'] is not None else 'withheld'}; simple-path estimate {o['path_estimate_percentage']}%; candidate: {o['potential_ubo']}" for o in own.get('owners',[])) or 'Ownership workflow not run; no candidate determination available.')
    for number,title,paths in [(5,'Direct ownership paths',[p for p in own.get('paths',[]) if p['depth']==1]),(6,'Indirect ownership paths',[p for p in own.get('paths',[]) if p['depth']>1])]:
        body='\n'.join(f"Entity IDs {' > '.join(map(str,p['entity_ids']))}: {p['attributable_percentage']}% | {', '.join(p['evidence'])}" for p in paths)
        if number==5: body='\n'.join(f"Entity #{r['owner_entity_id']} > #{r['owned_entity_id']}: {str(r['ownership_percentage'])+'%' if r['ownership_percentage'] is not None else 'unknown percentage'} | REL-{r['id']} / SRC-{r['source_id']}" for r in own.get('direct_relationships',[]))
        section(f'{number}. {title}',body or 'No paths recorded in this snapshot.')
    section('7. Graph findings','\n'.join(f"{f['indicator_name']}: {f['description']} [{', '.join(f['evidence'])}]" for f in report.get('algorithmic_indicators',[])) or 'No graph findings snapshot available.')
    section('8. Risk assessment',f"Observed score {risk['score']}/100 | {risk['category']} | {risk['data_completeness']}% indicator coverage. {risk['score_interpretation']}")
    rows=[[text('Indicator'),text('Score'),text('Weight'),text('Points')]]
    for i in risk['indicators']: rows.append([text(i['name']),text(i['score'] if i['available'] else 'Unavailable'),text(f"{i['weight']}%"),text(i['contribution'])])
    table=Table(rows,colWidths=[210,110,90,90],repeatRows=1,hAlign='LEFT'); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f1ef')),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d8e1e5')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7)])); story.append(table)
    ml=report.get('model_prediction',{'status':'unavailable'})
    section('9. Experimental ML output',f"Status: {ml['status']} | Model version: {ml.get('model_version') or 'Unavailable'}\nNovelty score: {ml.get('anomaly_score','Unavailable')}\n{ml.get('explanation',ml.get('reason','No model output recorded.'))}\nInputs: "+', '.join(f'{k}={round(v,4) if isinstance(v,float) else v}' for k,v in ml.get('features',{}).items())+'\nTraining data: '+ml.get('training_data','Unavailable'))
    section('10. Evidence references','\n'.join(own.get('evidence',[])) or f"SRC-{target['source_id']}")
    section('11. Data limitations','\n'.join(risk['missing_information']))
    section('12. Recommendations','\n'.join(risk['recommended_next_steps']))
    section('13. Analyst judgments','\n'.join(n['note'] for n in snapshot.get('notes',[])) or 'No analyst notes recorded.')
    section('14. Reviewer decision',f"Reviewer ID: {inv.get('reviewer_id')} | Decision: {inv.get('decision') or 'Pending / not reviewed'} | Reviewed at: {inv.get('reviewed_at') or 'Not reviewed'}")
    section('15. Responsible use',risk['disclaimer']+' Synthetic demo data must not support real-world decisions. Human review is required. No sanctions, PEP or adverse-media screening is connected.')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#5e727b')); canvas.drawString(44,26,'OwnershipGraph AI | Internal investigation | '+risk['version']); canvas.drawRightString(551,26,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue(),'application/pdf'
