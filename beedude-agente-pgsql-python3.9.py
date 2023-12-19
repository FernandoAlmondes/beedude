a
    ���e�"  �                   @   s�   d dl Z d dlZd dlmZ d dlZd dlZd dlmZ e j�	dd� e�
�  d dlmZmZ dZe jdd	d
� e j�dddd�Zed� ed� ed� eej�� �� �Zdd� Zdd� Zdd� Zdd� Zdd� Zdd� Ze�  dS )�    N)�sleep)�configZDJANGO_SETTINGS_MODULEzbeedude.settings)�Elemento�Item�
   z/opt/bee/beedude/tmpT)�exist_okZoptZbeeZbeedude�tmpz$---> Desenvolvido por: Bee Solutionsz---> Autor: Fernando Almondesz---> Sistema: Beedudec            
   
   C   s�  t d� td�td�td�td�td�d�} dt� d	�}d
t� d�}�zz�tjf i | ��}|�� }|�|� |�� }t	|dddd��F}|r�dd� |j
D �ng }t�|�}|�|� |�|� W d   � n1 s�0    Y  W n6 tj�y }	 zt d|	� �� W Y d }	~	n
d }	~	0 0 W dt� v �r0|�r0|��  dt� v �r�|�r�|��  n6dt� v �rf|�rf|��  dt� v �r�|�r�|��  0 d S )NzI--> Iniciando conexao com o banco de dados do Zabbix (Tabela de Hosts)...�DB_HOST_ZABBIX�DB_PORT_ZABBIX�DB_NAME_ZABBIX�DB_USER_ZABBIX�DB_PASSWORD_ZABBIX��hostZportZdatabase�userZpassworda  
        select ht.name host, ht.hostid,it.name item, it.itemid ,hu.value status,TO_TIMESTAMP(hu.clock) horario,concat('1') as node from items it 
        inner join hosts ht on (it.hostid = ht.hostid)
        inner join hosts_groups hg on (hg.hostid = ht.hostid)
        inner join hstgrp hst on (hst.groupid = hg.groupid)
        inner join (select itemid, max(clock) as max_clock from history_uint group by itemid) as max_hu on max_hu.itemid = it.itemid
        inner join history_uint hu on (hu.itemid = max_hu.itemid and max_hu.max_clock = hu.clock)
        where it.hostid in (select hostid from hosts where status = 0 and flags = 0) and it.key_ = 'icmpping' and hst.name in ('BEEDUDE')
        group by it.itemid, ht.name, ht.hostid, it.name, it.itemid, hu.value, horario, node limit z;
    �/�/tabela_hosts.csv�w� �utf-8��newline�encodingc                 S   s   g | ]}|d  �qS �r   � ��.0Zdescr   r   �beedude-agente-pgsql.py�
<listcomp>C   �    z(conecta_zabbix_hosts.<locals>.<listcomp>�$Erro ao conectar ao banco de dados: �cursor�conexao)�printr   �nodesr   �psycopg2�connectr!   �execute�fetchall�open�description�csv�writer�writerow�	writerows�Error�locals�close�
Zconexao_bancoZconsulta_sqlZnome_arquivo_csvr"   r!   Z
resultadosZarquivo_csvZcolunasZescritor_csvZerror   r   r   �conecta_zabbix_hosts   s>    �	�


,&
�r3   c            
   
   C   s~  t d� td�td�td�td�td�d�} d}d	t� d
�}�zz�tjf i | ��}|�� }|�|� |�� }t|dddd��F}|r�dd� |j	D �ng }t
�|�}|�|� |�|� W d   � n1 s�0    Y  W n6 tj�y
 }	 zt d|	� �� W Y d }	~	n
d }	~	0 0 W dt� v �r(|�r(|��  dt� v �rz|�rz|��  n6dt� v �r^|�r^|��  dt� v �rx|�rx|��  0 d S )NzI--> Iniciando conexao com o banco de dados do Zabbix (Tabela de Items)...r	   r
   r   r   r   r   a�  
        select ht.hostid as hostid,ht.name as host,it.itemid as itemid,it.name as item,
        coalesce(hu.value, 0) as valor,
        concat(CASE WHEN (it.name like '%status%' or it.name like '%Link down%') THEN coalesce(hu.value, '0') ELSE '0' END) AS status,
        coalesce(TO_TIMESTAMP(hu.clock), '2000-01-01 00:00:00') as horario
        from items it
        inner join hosts ht on (ht.hostid = it.hostid)
        inner join hosts_groups hg on (hg.hostid = ht.hostid)
        inner join hstgrp hst on (hst.groupid = hg.groupid)
        left join (select itemid, max(clock) as max_clock from history_uint group by itemid) AS max_hu ON max_hu.itemid = it.itemid
        left join history_uint hu on hu.itemid = max_hu.itemid and hu.clock = max_hu.max_clock
        where (it.name like '%Bits r%' or it.name like '%Bits s%' or it.name like '%gei_%' or it.name like '%status%')
        and it.name not like ('%IFALIAS%')
        and it.name not like '%Vlan%' and it.name not like '%vlan%'
        and it.name not like '%{#IFNAME}%' and it.name not like '%{#SNMPVALUE}%' and it.name not like '%Fan%'
        and ht.status = 0 and ht.flags != 2 and it.status = 0 and hst.name in ('BEEDUDE');
    r   �/tabela_items.csvr   r   r   r   c                 S   s   g | ]}|d  �qS r   r   r   r   r   r   r   �   r   z(conecta_zabbix_items.<locals>.<listcomp>r    r!   r"   )r#   r   r   r%   r&   r!   r'   r(   r)   r*   r+   r,   r-   r.   r/   r0   r1   r2   r   r   r   �conecta_zabbix_itemsZ   s:    �	


,&
�r5   c            	      C   s�   dt � d�} t| ddd���}tj|dd�}|D ]�}t|� dd	� }z||d
 �}W n tyh   d }Y n0 z||d �}W n ty�   d }Y n0 tjjdg|d |d |d |d ||d�d�\}}q.W d   � n1 s�0    Y  d S )Nr   z/lista-hosts-edges.csv�rr   �r   �;�Z	delimiterc                 S   s,   zt jj| d�W S  t jy&   Y d S 0 d S )N��codigo)r   �objects�getZDoesNotExistr:   r   r   r   �get_elemento_instance�   s    z,importa_edges.<locals>.get_elemento_instance�host_a�host_b�hostidr;   �label�status�node)r;   rB   rC   rD   r?   r@   �r;   �defaults)	r   r)   r+   �
DictReaderr#   �KeyErrorr   r<   �update_or_create)	�csv_file_path�file�
csv_reader�rowr>   Zhost_a_instanceZhost_b_instance�item�createdr   r   r   �importa_edges�   s0    

��rP   c               
   C   s�   t d� dt� d�} t| ddd��d}tj|dd�}|D ]@}tjjt|d	 �t|d	 �|d
 |d d|d d�d�\}}q6W d   � n1 s�0    Y  d S )Nz'--> Importando atualizacao dos hosts...r   r   r6   r   r7   �,r9   rA   r   rC   �   �horario)r;   rB   rC   rD   rS   rE   )	r#   r   r)   r+   rG   r   r<   rI   �int�rJ   rK   rL   rM   rN   rO   r   r   r   �importa_hosts�   s    

��rV   c               
   C   s�   t d� dt� d�} t| ddd���}tj|dd�}|D ]p}tjjt|d	 �t|d	 �|d
 d |d  |d dkrz|d nd|d dkr�|d nd|d d�d�\}}q6W d   � n1 s�0    Y  d S )Nz'--> Importando atualizacao dos items...r   r4   r6   r   r7   rQ   r9   �itemidr   z | rN   rC   r   rR   �valorr   rS   )rW   ZnomerC   rX   rS   )rW   rF   )	r#   r   r)   r+   rG   r   r<   rI   rT   rU   r   r   r   �importa_items�   s    

��rY   c                   C   sF   t d� t�  t�  t�  t�  t d� t d� t d� td� q d S )Nz--> Atualizando dados...zE
--------------------------------------------------------------------z2
--> Aguardando 10 segundos ate a nova consulta...r   )r#   r3   r5   rV   rY   r   r   r   r   r   �executa_atualizacao�   s    rZ   )�osr+   �timer   r%   ZdjangoZdecoupler   �environ�
setdefaultZsetupZgrafo.modelsr   r   r$   �makedirs�path�joinr   r#   �listr<   �all�valuesZ	elementosr3   r5   rP   rV   rY   rZ   r   r   r   r   �<module>   s,   =D%