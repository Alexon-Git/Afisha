import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import ImportDashboard from './ImportDashboard';
import { importApi } from '../services/api';
jest.mock('../services/api', () => ({ importApi: {sources:jest.fn(),runs:jest.fn(),start:jest.fn(),candidates:jest.fn(),candidate:jest.fn(),approve:jest.fn(),reject:jest.fn(),promote:jest.fn(),link:jest.fn(),edit:jest.fn(),recheck:jest.fn()} }));
const candidate={id:5,revision:2,title:'Business fixture',source_url:'https://example.invalid/event',original_start:'ambiguous',
 review_status:'pending',start_at:null,time_resolution:'ambiguous',city:'Новосибирск',venue_name:'Hall',warnings:['ambiguous_time'],
 field_provenance:{url:'https://example.invalid/event'},matches:[{id:7,event_id:9,reason_codes:['same_url'],score:'1.0'}]};
let container,root;
const button=text=>Array.from(container.querySelectorAll('button')).find(x=>x.textContent===text);
const input=text=>Array.from(container.querySelectorAll('label')).find(x=>x.textContent.startsWith(text)).querySelector('input,select');
const click=node=>act(async()=>node.dispatchEvent(new MouseEvent('click',{bubbles:true})));
const change=(node,value)=>act(()=>Simulate.change(node,{target:{value}}));
const render=()=>act(async()=>root.render(<ImportDashboard/>));
const open=async()=>{await render();await click(button('Business fixture — pending'));};
beforeEach(()=>{
 jest.clearAllMocks();global.IS_REACT_ACT_ENVIRONMENT=true;
 container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);
 importApi.sources.mockResolvedValue({data:[{id:1,name:'Fixture source',state:'enabled',robots_state:'allowed'}]});
 importApi.runs.mockResolvedValue({data:[]});importApi.candidates.mockResolvedValue({data:{items:[candidate],total_pages:1}});
 importApi.candidate.mockResolvedValue({data:candidate});
});
afterEach(async()=>{await act(async()=>root.unmount());container.remove();});
test('shows provenance ambiguity and matches, without implicit publishing',async()=>{
 await open();expect(container.textContent).toContain('Время Новосибирска: Неоднозначно');
 expect(container.textContent).toContain('Event 9: same_url');expect(container.textContent).toContain('Новый Event создаётся только');
 expect(importApi.approve).not.toHaveBeenCalled();expect(importApi.promote).not.toHaveBeenCalled();
});
test('approve and draft creation are separate explicit actions',async()=>{
 importApi.approve.mockResolvedValue({data:{...candidate,review_status:'approved'}});
 importApi.promote.mockResolvedValue({data:{...candidate,review_status:'converted',linked_event_id:30}});
 await open();act(()=>Simulate.change(input('Подтверждаю:'),{target:{checked:true}}));
 await click(button('Одобрить'));expect(importApi.approve).toHaveBeenCalledWith(candidate,true);
 expect(importApi.promote).not.toHaveBeenCalled();expect(button('Создать Event draft').disabled).toBe(false);
 await click(button('Создать Event draft'));expect(container.textContent).toContain('Создан черновик. Проверка');
 expect(importApi.promote).toHaveBeenCalledWith({...candidate,review_status:'approved'});
});
test('existing Event link never publishes or updates Event',async()=>{
 importApi.candidate.mockResolvedValue({data:{...candidate,review_status:'approved'}});
 importApi.link.mockResolvedValue({data:{...candidate,review_status:'linked',linked_event_id:9}});
 await open();change(input('ID существующего Event'),'9');await click(button('Привязать к Event'));
 expect(container.textContent).toContain('существующее мероприятие не изменено');
 expect(importApi.link).toHaveBeenCalledWith({...candidate,review_status:'approved'},9);expect(importApi.promote).not.toHaveBeenCalled();
});
test('enqueue retries same idempotency key after error',async()=>{
 importApi.start.mockRejectedValue({response:{data:{detail:'source_not_authorized'}}});
 await render();change(input('Источник'),'1');change(input('URL страницы'),'https://example.invalid/event');
 await click(button('Запустить импорт'));expect(container.querySelector('[role="alert"]').textContent).toBe('source_not_authorized');
 expect(importApi.start).toHaveBeenCalledWith(1,'https://example.invalid/event',expect.any(String));
 const key=importApi.start.mock.calls[0][2];await click(button('Запустить импорт'));
 expect(importApi.start.mock.calls[1][2]).toBe(key);
});
test('reject requires note, time correction is explicit and revisioned',async()=>{
 importApi.edit.mockResolvedValue({data:{...candidate,revision:3,review_status:'needs_review'}});
 await open();expect(button('Отклонить').disabled).toBe(true);
 change(input('Дата ISO 8601 с offset'),'2026-11-23T18:00:00+07:00');change(input('Примечание редактора'),'Confirmed');
 await click(button('Уточнить факты (снять одобрение)'));
 expect(importApi.edit).toHaveBeenCalledWith(candidate,{start_at:'2026-11-23T18:00:00+07:00',city:'Новосибирск',venue_name:'Hall',review_note:'Confirmed'});
});
